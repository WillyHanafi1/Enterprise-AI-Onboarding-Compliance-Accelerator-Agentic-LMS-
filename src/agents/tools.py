"""
Agent Tools.

Defines tool functions that LangGraph agent nodes can invoke.
Tools are registered with agents via LangChain's @tool decorator
or passed as a tools list to ChatModel.bind_tools().

Tools defined here:
    - retrieve_internal_policies: Semantic search on ingested SOPs
    - generate_evaluation_rubric:  Creates grading rubric (Phase 3)
"""

import logging

from langchain_core.documents import Document
from langchain_core.tools import tool

from src.ingestion.pipeline import get_vector_store

logger = logging.getLogger(__name__)

# === Constants ===
DEFAULT_TOP_K = 5


@tool
def retrieve_internal_policies(query: str) -> str:
    """
    Searches ingested SOP documents for passages relevant to the query.

    Uses MMR (Maximal Marginal Relevance) search for diverse, non-redundant
    results. Returns the top-5 most relevant chunks with source metadata.

    This tool is used by the Explainer and Planner agents to ground
    their responses strictly in official company policies.

    Args:
        query: The natural language search query.

    Returns:
        A formatted string containing the retrieved document passages
        with source attribution (filename, page number).
    """
    vector_store = get_vector_store()

    # MMR search balances relevance with diversity to avoid redundant chunks
    results: list[Document] = vector_store.max_marginal_relevance_search(
        query=query,
        k=DEFAULT_TOP_K,
        fetch_k=DEFAULT_TOP_K * 4,  # Fetch more candidates for MMR reranking
    )

    if not results:
        logger.warning("No results found for query: '%s'", query)
        return "No relevant documents found for this query. Please verify that SOP documents have been ingested."

    # Format results with source attribution
    formatted_chunks: list[str] = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        formatted_chunks.append(f"[Source {i}: {source}, Page {page}]\n{doc.page_content}")

    logger.info("Retrieved %d chunks for query: '%s'", len(results), query[:80])
    return "\n\n---\n\n".join(formatted_chunks)


def retrieve_documents_with_scores(
    query: str, top_k: int = DEFAULT_TOP_K
) -> list[tuple[Document, float]]:
    """
    Retrieves documents with their similarity scores.

    This is a utility function (not a LangChain tool) used for
    evaluation, debugging, and testing retrieval quality.

    Args:
        query: The natural language search query.
        top_k: Number of results to return.

    Returns:
        A list of (Document, score) tuples sorted by relevance.
        Scores are cosine similarity values between 0 and 1.
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=top_k,
    )

    logger.info(
        "Retrieved %d scored results for query: '%s' (top score: %.3f)",
        len(results),
        query[:80],
        results[0][1] if results else 0.0,
    )
    return results


@tool
def generate_evaluation_rubric(topic: str) -> str:
    """
    Generates a grading rubric for evaluating a user's knowledge on a specific topic.

    This tool is used by the Assessor agent to standardize how it grades
    user responses to quiz questions.

    Args:
        topic: The topic being evaluated.

    Returns:
        A structured string containing the grading rubric criteria.
    """
    rubric = f"""
Evaluation Rubric for Topic: {topic}

Pass (Score 80-100):
- Demonstrates clear understanding of the core concepts of {topic}.
- Actions align with company policy and best practices.
- Identifies critical risks and appropriate mitigation strategies.

Needs Review (Score 50-79):
- Partial understanding, but misses key details or nuance.
- Mentions general concepts but fails to apply specific company policy.

Fail (Score 0-49):
- Fundamental misunderstanding of {topic}.
- Proposes actions that violate security, compliance, or HR policies.
- Unable to identify the correct procedures.

Instructions for Grader:
1. Score the response strictly based on alignment with company policy.
2. Provide constructive feedback indicating exactly what policy was missed.
3. If score < 80, explain why it failed the threshold.
"""
    return rubric
