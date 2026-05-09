import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.assessor import assessor_node
from src.agents.explainer import explainer_node
from src.agents.planner import planner_node
from src.agents.tools import generate_evaluation_rubric


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for the test session to pass validation."""
    os.environ["GEMINI_API_KEY"] = "mock_api_key"
    os.environ["LANGFUSE_PUBLIC_KEY"] = "mock_pk"
    os.environ["LANGFUSE_SECRET_KEY"] = "mock_sk"
    yield
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
    os.environ.pop("LANGFUSE_SECRET_KEY", None)


class TestPlannerAgent:
    @patch("src.agents.planner.get_llm")
    def test_planner_generates_syllabus(self, mock_get_llm):
        # Mock the structured output
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured

        # Define what the LLM returns
        mock_response = MagicMock()
        mock_response.syllabus = ["Topic 1", "Topic 2"]
        mock_structured.invoke.return_value = mock_response

        state = {"employee_role": "Software Engineer"}
        result = planner_node(state)

        assert result["syllabus"] == ["Topic 1", "Topic 2"]
        assert result["current_agent"] == "planner_node"

    @patch("src.agents.planner.get_llm")
    def test_planner_fallback_on_error(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured

        mock_structured.invoke.side_effect = Exception("API Error")

        state = {}
        result = planner_node(state)

        assert "General Onboarding" in result["syllabus"]


class TestExplainerAgent:
    @patch("src.agents.explainer.create_react_agent")
    @patch("src.agents.explainer.get_llm")
    def test_explainer_answers_question(self, mock_get_llm, mock_create_agent):
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="What is the password policy?"),
                AIMessage(content="The policy is 12 chars.")
            ]
        }

        state = {
            "current_topic": "Password Policy",
            "messages": [HumanMessage(content="What is the password policy?")]
        }
        result = explainer_node(state)

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "The policy is 12 chars."
        assert result["current_agent"] == "explainer_node"

    @patch("src.agents.explainer.create_react_agent")
    @patch("src.agents.explainer.get_llm")
    def test_explainer_fallback_on_error(self, mock_get_llm, mock_create_agent):
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        mock_agent.invoke.side_effect = Exception("API Error")

        state = {"current_topic": "Data Classification", "messages": []}
        result = explainer_node(state)

        assert "error" in result["messages"][0].content.lower()


class TestAssessorAgent:
    @patch("src.agents.assessor.create_react_agent")
    @patch("src.agents.assessor.get_llm")
    def test_assessor_asks_initial_question(self, mock_get_llm, mock_create_agent):
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="I am ready for the quiz."),
                AIMessage(content="What is the policy?")
            ]
        }

        state = {
            "current_topic": "Password Policy",
            "messages": [HumanMessage(content="I am ready for the quiz.")]
        }
        result = assessor_node(state)

        assert "messages" in result
        assert "quiz_score" not in result
        assert result["current_agent"] == "assessor_node"

    @patch("src.agents.assessor.create_react_agent")
    @patch("src.agents.assessor.get_llm")
    def test_assessor_grades_correct_answer(self, mock_get_llm, mock_create_agent):
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        # Simulate LLM returning a tool call to submit_grade
        mock_tool_call = {
            "name": "submit_grade",
            "args": {"score": 90, "feedback": "Great job!"},
            "id": "123",
            "type": "tool_call"
        }
        mock_agent.invoke.return_value = {
            "messages": [
                AIMessage(content="What are the requirements?"),
                HumanMessage(content="12 chars."),
                AIMessage(content="", tool_calls=[mock_tool_call])
            ]
        }

        state = {
            "current_topic": "Password Policy",
            "messages": [
                AIMessage(content="What are the requirements?"),
                HumanMessage(content="12 chars.")
            ]
        }
        result = assessor_node(state)

        assert result["quiz_score"] == 90
        assert result["assessment_history"][0]["passed"] is True
        assert result["failed_attempts"] == 0
        assert result["completed_topics"] == ["Password Policy"]

    @patch("src.agents.assessor.create_react_agent")
    @patch("src.agents.assessor.get_llm")
    def test_assessor_grades_wrong_answer(self, mock_get_llm, mock_create_agent):
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        # Simulate LLM returning a failing grade
        mock_tool_call = {
            "name": "submit_grade",
            "args": {"score": 40, "feedback": "Wrong!"},
            "id": "124",
            "type": "tool_call"
        }
        mock_agent.invoke.return_value = {
            "messages": [
                AIMessage(content="What are the requirements?"),
                HumanMessage(content="123456"),
                AIMessage(content="", tool_calls=[mock_tool_call])
            ]
        }

        state = {
            "current_topic": "Password Policy",
            "messages": [
                AIMessage(content="What are the requirements?"),
                HumanMessage(content="123456")
            ]
        }
        result = assessor_node(state)

        assert result["quiz_score"] == 40
        assert result["assessment_history"][0]["passed"] is False
        assert result["failed_attempts"] == 1


class TestTools:
    def test_generate_evaluation_rubric(self):
        rubric = generate_evaluation_rubric.invoke({"topic": "Data Security"})
        assert "Data Security" in rubric
        assert "Score 80-100" in rubric
        assert "Score 0-49" in rubric

