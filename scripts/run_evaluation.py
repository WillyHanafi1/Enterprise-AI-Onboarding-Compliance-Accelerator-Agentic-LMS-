"""
Evaluation Pipeline — Faithfulness & Answer Relevancy.

Runs the Explainer Agent against the gold-standard evaluation dataset
and uses an LLM judge to score each response on:
  - Faithfulness: Does the response match the ground truth?
  - Relevancy: Does the response directly answer the question?

BUG-1 FIX: The script now uses SQLite checkpointer by default to avoid
requiring a running Postgres instance. Use --postgres flag to force Postgres.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.config import get_settings

# Setup settings
settings = get_settings()

JUDGE_PROMPT_FAITHFULNESS = """
You are an expert evaluator assessing the FAITHFULNESS of an AI Assistant's response.
FAITHFULNESS measures how accurately the response reflects the provided "Ground Truth" answer.

Ground Truth: {expected_answer}
AI Response: {ai_response}

Criteria:
1. Score 1.0 if the AI response captures the core factual details of the Ground Truth.
2. Score 0.5 if the AI response is partially correct but misses key details or includes minor hallucinations.
3. Score 0.0 if the AI response contradicts the Ground Truth or provides incorrect information.

Provide your evaluation in JSON format:
{{
  "score": float,
  "reason": "short explanation"
}}
"""

JUDGE_PROMPT_RELEVANCY = """
You are an expert evaluator assessing the ANSWER RELEVANCY of an AI Assistant's response.
RELEVANCY measures how directly and effectively the response addresses the user's question.

Question: {question}
AI Response: {ai_response}

Criteria:
1. Score 1.0 if the AI response directly answers the question without unnecessary fluff.
2. Score 0.5 if the AI response is vague, indirect, or requires the user to infer the answer.
3. Score 0.0 if the AI response is completely off-topic or fails to answer the question.

Provide your evaluation in JSON format:
{{
  "score": float,
  "reason": "short explanation"
}}
"""


def extract_text_from_content(content):
    """Handles list-based content from newer Gemini models."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        return "".join(text_parts)
    return str(content)


def _build_eval_graph():
    """
    Build a graph with SQLite checkpointer for evaluation.

    BUG-1 FIX: Uses SQLite instead of Postgres so the eval pipeline
    doesn't depend on an external database service.
    """
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    from src.graph.workflow import build_graph

    # Use an in-memory SQLite DB for evaluation (ephemeral, no persistence needed)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = build_graph(checkpointer=checkpointer)
    return graph, conn


async def run_evaluation():
    print("Starting Evaluation Pipeline...")

    # BUG-1 FIX: Build a standalone graph with SQLite (no Postgres required)
    graph, db_conn = _build_eval_graph()
    judge_llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        api_key=settings.GEMINI_API_KEY,
    )

    # Load dataset
    dataset_path = Path("data/evaluation_dataset.json")
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    results = []
    total_faithfulness = 0
    total_relevancy = 0
    successful_evals = 0

    total_items = len(dataset)
    print(f"Evaluating {total_items} pairs from dataset...", flush=True)

    for i, item in enumerate(dataset):
        question = item["question"]
        expected = item["expected_answer"]

        print(f"[{i+1}/{total_items}] Q: {question}", flush=True)

        # Invoke Explainer Agent (via graph)
        # Each eval item gets a unique thread_id
        config = {"configurable": {"thread_id": f"eval_{i}_{datetime.now().timestamp()}"}}

        try:
            # Pre-populate syllabus and role to bypass planner
            # This routes directly to the explainer via the conditional entry point
            initial_state = {
                "messages": [HumanMessage(content=question)],
                "syllabus": ["General Onboarding"],
                "current_topic": "General Onboarding",
                "employee_role": "General Employee",
                "employee_name": "Eval User",
                "completed_topics": [],
                "quiz_score": 0,
                "failed_attempts": 0,
                "assessment_history": [],
                "is_certified": False,
                "requires_human_review": False,
                "current_agent": None,
            }
            # Use sync invoke since we're using SqliteSaver (sync checkpointer)
            response = graph.invoke(initial_state, config)

            # Find the last AI message
            ai_content = ""
            for msg in reversed(response.get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content:
                    ai_content = extract_text_from_content(msg.content)
                    break

            if not ai_content:
                print(f"  - WARNING: No AI response generated", flush=True)
                results.append({
                    "id": i,
                    "question": question,
                    "error": "No AI response generated"
                })
                continue

            # 1. Evaluate Faithfulness
            f_eval_resp = await judge_llm.ainvoke([
                SystemMessage(content="You are a rigorous JSON-only evaluator. Return ONLY valid JSON."),
                HumanMessage(content=JUDGE_PROMPT_FAITHFULNESS.format(expected_answer=expected, ai_response=ai_content))
            ])
            f_eval_text = extract_text_from_content(f_eval_resp.content).strip()
            # Clean JSON if LLM included markdown blocks
            if "```json" in f_eval_text:
                f_eval_text = f_eval_text.split("```json")[1].split("```")[0].strip()
            elif "```" in f_eval_text:
                f_eval_text = f_eval_text.split("```")[1].split("```")[0].strip()
            f_eval = json.loads(f_eval_text)

            # 2. Evaluate Relevancy
            r_eval_resp = await judge_llm.ainvoke([
                SystemMessage(content="You are a rigorous JSON-only evaluator. Return ONLY valid JSON."),
                HumanMessage(content=JUDGE_PROMPT_RELEVANCY.format(question=question, ai_response=ai_content))
            ])
            r_eval_text = extract_text_from_content(r_eval_resp.content).strip()
            if "```json" in r_eval_text:
                r_eval_text = r_eval_text.split("```json")[1].split("```")[0].strip()
            elif "```" in r_eval_text:
                r_eval_text = r_eval_text.split("```")[1].split("```")[0].strip()
            r_eval = json.loads(r_eval_text)

            # Store results
            results.append({
                "id": i,
                "question": question,
                "expected_answer": expected,
                "ai_response": ai_content[:500],  # Truncate for readability
                "faithfulness": f_eval,
                "relevancy": r_eval,
                "source": item.get("source_document", "unknown")
            })

            f_score = f_eval.get("score", 0)
            r_score = r_eval.get("score", 0)
            total_faithfulness += f_score
            total_relevancy += r_score
            successful_evals += 1
            print(f"  [OK] Faithfulness={f_score}, Relevancy={r_score}", flush=True)

        except Exception as e:
            print(f"  [FAIL] Error: {e}", flush=True)
            results.append({
                "id": i,
                "question": question,
                "error": str(e)
            })

    # Cleanup SQLite
    db_conn.close()

    # Summary
    avg_faithfulness = total_faithfulness / successful_evals if successful_evals else 0
    avg_relevancy = total_relevancy / successful_evals if successful_evals else 0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_items": total_items,
        "items_evaluated_successfully": successful_evals,
        "items_failed": total_items - successful_evals,
        "avg_faithfulness": round(avg_faithfulness, 4),
        "avg_relevancy": round(avg_relevancy, 4),
        "detailed_results": results
    }

    # Save results
    output_path = Path("data/eval_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 50)
    print("EVALUATION COMPLETE")
    print("=" * 50)
    print(f"Successfully Evaluated: {successful_evals}/{total_items}")
    print(f"Avg Faithfulness: {avg_faithfulness:.4f}")
    print(f"Avg Relevancy:    {avg_relevancy:.4f}")
    print(f"Detailed results saved to {output_path}")
    print("=" * 50)

if __name__ == "__main__":
    if sys.platform == "win32":
        # Fix for Psycopg + Windows asyncio (ProactorEventLoop not supported by Psycopg)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_evaluation())
