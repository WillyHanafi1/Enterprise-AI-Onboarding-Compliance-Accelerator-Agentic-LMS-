"""
API Integration Tests — Phase 5.

Tests the complete API surface with mocked LLM calls:
    1. Health check endpoint
    2. POST /sessions — create session
    3. GET /sessions/{id}/status — get progress
    4. POST /sessions/{id}/chat/sync — synchronous chat
    5. POST /sessions/{id}/approve — supervisor approval (HITL)
    6. POST /sessions/{id}/reject — supervisor rejection
    7. Full end-to-end flow: create → learn → quiz → approve → certify
    8. Error cases: 404 session, double approve, chat after certification
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.api.server import create_app

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for the test session."""
    os.environ["GEMINI_API_KEY"] = "mock_api_key"
    os.environ["LANGFUSE_PUBLIC_KEY"] = "mock_pk"
    os.environ["LANGFUSE_SECRET_KEY"] = "mock_sk"
    yield
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
    os.environ.pop("LANGFUSE_SECRET_KEY", None)


@pytest.fixture
def client():
    """
    Creates a test client with a fresh graph using MemorySaver.

    We patch dependencies to use an in-memory graph instead of
    the default SQLite checkpointer, ensuring test isolation.
    """
    from langgraph.checkpoint.memory import MemorySaver

    from src.graph.workflow import build_graph

    memory = MemorySaver()
    test_graph = build_graph(checkpointer=memory)

    # Patch the dependency module to use our test graph
    with (
        patch("src.api.dependencies._graph_instance", test_graph),
        patch("src.api.dependencies._checkpointer_instance", memory),
        patch("src.api.server.init_graph"),
        patch("src.api.server.shutdown_graph"),
    ):
        app = create_app()

        # Override the dependency to return our test graph
        from src.api.dependencies import get_graph_instance

        app.dependency_overrides[get_graph_instance] = lambda: test_graph

        with TestClient(app) as c:
            yield c


# ============================================================
# Test 1: Health Check
# ============================================================


class TestHealthCheck:
    def test_health_returns_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "environment" in data


# ============================================================
# Test 2: Session Creation
# ============================================================


class TestSessionCreation:
    @patch("src.agents.planner.get_llm")
    def test_create_session_success(self, mock_get_llm, client):
        """POST /sessions should create a session and return welcome message."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured

        mock_response = MagicMock()
        mock_response.syllabus = ["Security Policy", "Code of Conduct"]
        mock_structured.invoke.return_value = mock_response

        response = client.post(
            "/api/v1/sessions",
            json={
                "employee_name": "Alice",
                "employee_role": "Software Engineer",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "welcome_message" in data
        assert len(data["syllabus"]) == 2
        assert "Alice" in data["welcome_message"]

    def test_create_session_missing_fields(self, client):
        """POST /sessions with missing fields should return 422."""
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422

    def test_create_session_empty_name(self, client):
        """POST /sessions with empty name should return 422."""
        response = client.post(
            "/api/v1/sessions",
            json={"employee_name": "", "employee_role": "QA"},
        )
        assert response.status_code == 422


# ============================================================
# Test 3: Session Status
# ============================================================


class TestSessionStatus:
    @patch("src.agents.planner.get_llm")
    def test_get_status_after_creation(self, mock_get_llm, client):
        """GET /sessions/{id}/status should return current state."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured

        mock_response = MagicMock()
        mock_response.syllabus = ["Topic A"]
        mock_structured.invoke.return_value = mock_response

        # Create session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"employee_name": "Bob", "employee_role": "PM"},
        )
        session_id = create_resp.json()["session_id"]

        # Get status
        status_resp = client.get(f"/api/v1/sessions/{session_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["employee_name"] == "Bob"
        assert data["employee_role"] == "PM"
        assert data["is_certified"] is False

    def test_status_nonexistent_session(self, client):
        """GET /sessions/unknown/status should return 404."""
        response = client.get("/api/v1/sessions/nonexistent-id/status")
        assert response.status_code == 404


# ============================================================
# Test 4: Chat (Sync)
# ============================================================


class TestChatSync:
    @patch("src.agents.explainer.create_react_agent")
    @patch("src.agents.explainer.get_llm")
    @patch("src.agents.router.get_llm")
    @patch("src.agents.planner.get_llm")
    def test_chat_learn_intent(
        self, mock_planner_llm, mock_router_llm, mock_explainer_llm,
        mock_create_agent, client
    ):
        """Chat with learn intent should return explainer response."""
        # Mock planner
        mock_p_llm = MagicMock()
        mock_p_structured = MagicMock()
        mock_planner_llm.return_value = mock_p_llm
        mock_p_llm.with_structured_output.return_value = mock_p_structured
        mock_p_response = MagicMock()
        mock_p_response.syllabus = ["Security"]
        mock_p_structured.invoke.return_value = mock_p_response

        # Create session
        create_resp = client.post(
            "/api/v1/sessions",
            json={"employee_name": "Carol", "employee_role": "Dev"},
        )
        session_id = create_resp.json()["session_id"]

        # Mock router
        mock_r_llm = MagicMock()
        mock_r_structured = MagicMock()
        mock_router_llm.return_value = mock_r_llm
        mock_r_llm.with_structured_output.return_value = mock_r_structured
        mock_r_result = MagicMock()
        mock_r_result.intent = "learn"
        mock_r_result.reasoning = "User wants to learn."
        mock_r_structured.invoke.return_value = mock_r_result

        # Mock explainer
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        mock_agent.invoke.return_value = {
            "messages": [
                AIMessage(content="Security policy requires 2FA for all employees.")
            ]
        }

        # Chat
        chat_resp = client.post(
            f"/api/v1/sessions/{session_id}/chat/sync",
            json={"message": "Teach me about security"},
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert data["session_id"] == session_id
        assert len(data["message"]) > 0

    def test_chat_nonexistent_session(self, client):
        """Chat with non-existent session should return 404."""
        response = client.post(
            "/api/v1/sessions/bad-id/chat/sync",
            json={"message": "hello"},
        )
        assert response.status_code == 404


# ============================================================
# Test 5: Supervisor Approve
# ============================================================


class TestSupervisorApprove:
    def test_approve_nonexistent_session(self, client):
        """Approve non-existent session should return 404."""
        response = client.post("/api/v1/sessions/bad-id/approve")
        assert response.status_code == 404

    @patch("src.agents.planner.get_llm")
    def test_approve_session_not_waiting(self, mock_get_llm, client):
        """Approve session that isn't at HITL gate should return 400."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_response = MagicMock()
        mock_response.syllabus = ["Topic"]
        mock_structured.invoke.return_value = mock_response

        create_resp = client.post(
            "/api/v1/sessions",
            json={"employee_name": "Dave", "employee_role": "QA"},
        )
        session_id = create_resp.json()["session_id"]

        # Try to approve — should fail because we haven't completed assessments
        approve_resp = client.post(f"/api/v1/sessions/{session_id}/approve")
        assert approve_resp.status_code == 400


# ============================================================
# Test 6: Supervisor Reject
# ============================================================


class TestSupervisorReject:
    def test_reject_nonexistent_session(self, client):
        """Reject non-existent session should return 404."""
        response = client.post("/api/v1/sessions/bad-id/reject")
        assert response.status_code == 404


# ============================================================
# Test 7: Full E2E API Flow
# ============================================================


class TestFullE2EAPIFlow:
    """
    Tests the complete onboarding lifecycle through the API:
        1. Create session
        2. Verify status
        3. Simulate HITL by directly manipulating graph state
        4. Approve certification
        5. Verify final state
    """

    @patch("src.agents.planner.get_llm")
    def test_full_lifecycle_with_hitl(self, mock_planner_llm, client):
        """Full lifecycle: create → HITL → approve → certified."""
        # Mock planner
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_planner_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_response = MagicMock()
        mock_response.syllabus = ["Topic 1"]
        mock_structured.invoke.return_value = mock_response

        # Step 1: Create session
        create_resp = client.post(
            "/api/v1/sessions",
            json={"employee_name": "Eve", "employee_role": "Engineer"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["session_id"]

        # Step 2: Verify status
        status_resp = client.get(f"/api/v1/sessions/{session_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["employee_name"] == "Eve"
        assert status_resp.json()["is_certified"] is False

        # Step 3: Simulate assessor passing all topics.
        # We update state as if assessor_node just completed with a passing grade,
        # then invoke to let the graph flow naturally:
        # grade_check → pass → advance_topic → topic_check → certify → interrupt_before(certifier_node)
        from src.api.dependencies import get_graph_instance
        graph = client.app.dependency_overrides[get_graph_instance]()
        config = {"configurable": {"thread_id": session_id}}

        # Set state as if assessor just graded pass
        graph.update_state(
            config,
            {
                "quiz_score": 95,
                "completed_topics": ["Topic 1"],
                "assessment_history": [
                    {"topic": "Topic 1", "score": 95, "passed": True}
                ],
            },
            as_node="assessor_node",
        )

        # Invoke the graph — should flow: grade_check(pass) → advance_topic → topic_check(certify) → INTERRUPT
        graph.invoke(None, config)

        # Verify HITL interrupt
        snapshot = graph.get_state(config)
        # The graph should be paused before certifier_node
        assert snapshot.next, "Graph should be paused at certifier_node (HITL)"
        assert "certifier_node" in snapshot.next

        # Step 4: Approve
        approve_resp = client.post(
            f"/api/v1/sessions/{session_id}/approve",
            json={"feedback": "Great work, Eve!"},
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["action"] == "approved"
        assert approve_data["is_certified"] is True

        # Step 5: Verify final state
        final_status = client.get(f"/api/v1/sessions/{session_id}/status")
        assert final_status.status_code == 200
        assert final_status.json()["is_certified"] is True


# ============================================================
# Test 8: Edge Cases
# ============================================================


class TestEdgeCases:
    @patch("src.agents.planner.get_llm")
    def test_chat_after_certification(self, mock_get_llm, client):
        """Chat on a certified session should return appropriate message."""
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.with_structured_output.return_value = mock_structured
        mock_response = MagicMock()
        mock_response.syllabus = ["Topic"]
        mock_structured.invoke.return_value = mock_response

        create_resp = client.post(
            "/api/v1/sessions",
            json={"employee_name": "Frank", "employee_role": "HR"},
        )
        session_id = create_resp.json()["session_id"]

        # Directly set certified
        from src.api.dependencies import get_graph_instance
        graph = client.app.dependency_overrides[get_graph_instance]()
        config = {"configurable": {"thread_id": session_id}}
        graph.update_state(config, {"is_certified": True})

        # Chat should tell user session is certified
        chat_resp = client.post(
            f"/api/v1/sessions/{session_id}/chat/sync",
            json={"message": "hello"},
        )
        assert chat_resp.status_code == 200
        assert "certified" in chat_resp.json()["message"].lower()
