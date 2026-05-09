import pytest
import json
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage
from src.api.dependencies import init_graph, get_graph_instance

@pytest.mark.asyncio
async def test_evaluation_pipeline_sanity():
    """
    Sanity check to ensure the graph can be invoked 
    and returns a valid response for evaluation.
    """
    init_graph()
    graph = get_graph_instance()
    
    config = {"configurable": {"thread_id": "sanity_test"}}
    initial_state = {
        "messages": [HumanMessage(content="What is the policy for public Wi-Fi?")],
        "syllabus": ["General Onboarding"],
        "employee_role": "General Employee"
    }
    
    response = await graph.ainvoke(initial_state, config)
    
    assert "messages" in response
    assert len(response["messages"]) > 0
    
    # Check if we got an AI response
    ai_msg = next((msg for msg in reversed(response["messages"]) if isinstance(msg, AIMessage)), None)
    assert ai_msg is not None
    assert len(ai_msg.content) > 0
    
    print(f"\nSanity check passed. AI Response: {ai_msg.content[:50]}...")
