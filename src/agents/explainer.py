import logging

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from src.agents.tools import retrieve_internal_policies
from src.core.llm import get_llm
from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)

def get_explainer_agent():
    """
    Creates and returns the Explainer Agent as a compiled sub-graph.
    
    This agent uses a state_modifier to dynamically inject the system prompt
    based on the current topic and role in the state.
    """
    llm = get_llm(temperature=0.3)
    tools = [retrieve_internal_policies]

    def state_modifier(state: dict) -> list:
        topic = state.get("current_topic", "General Onboarding")
        role = state.get("employee_role", "General Employee")
        
        system_prompt = f"""You are the Explainer Tutor for an Enterprise AI Onboarding system.
Your goal is to teach the user about the topic: '{topic}'.
The user's role is: '{role}'.

Instructions:
1. FIRST, determine if the user's question is related to company onboarding, policies, work procedures, or the current topic.
2. If the question IS relevant: Use the `retrieve_internal_policies` tool to search for ground-truth information, then explain it clearly.
3. If the question is NOT relevant (e.g., recipes, sports, celebrities, personal questions): Do NOT call any tools. Politely decline and redirect the user back to the current onboarding topic. Keep the refusal brief (1-2 sentences).
4. Explain retrieved policies in a clear, conversational, and encouraging tone.
5. Focus on actionable guidance: Tell the user what they NEED TO DO, not just what the policy says. Frame information as practical steps.
6. If the retrieved policies do not contain the answer, explicitly state that you don't know and do not invent information.
7. Keep your answers concise and relevant to the user's role.
"""
        # Return the system message followed by the history
        return [SystemMessage(content=system_prompt)] + state.get("messages", [])

    return create_react_agent(llm, tools, prompt=state_modifier)

# We keep this for backward compatibility if needed, but it's better to use the agent directly in the graph.
def explainer_node(state: OnboardingState) -> dict:
    logger.info("Running Explainer Agent for topic: %s", state.get("current_topic"))
    agent = get_explainer_agent()
    try:
        result = agent.invoke(state)
        # The react agent returns the full state including messages.
        # We only want to return the new messages to the parent graph.
        new_messages = result["messages"][len(state.get("messages", [])):]
    except Exception as e:
        logger.error("Explainer agent failed: %s", e)
        from langchain_core.messages import AIMessage
        new_messages = [AIMessage(content="I'm sorry, I encountered an error while trying to explain this topic.")]
        
    return {
        "messages": new_messages,
        "current_agent": "explainer_node"
    }
