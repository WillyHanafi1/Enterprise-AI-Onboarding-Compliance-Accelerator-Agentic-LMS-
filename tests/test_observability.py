import os
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from src.core.observability import mask_pii, get_langfuse_callback
from src.core.config import get_settings
from src.api.server import create_app
from src.api.dependencies import get_graph_instance

@pytest.fixture
def client():
    """
    Creates a test client with a fresh graph using MemorySaver.
    """
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
        app.dependency_overrides[get_graph_instance] = lambda: test_graph

        with TestClient(app) as c:
            yield c

class TestObservabilityLogic:
    def test_pii_masking_email(self):
        """Verify that emails are masked in strings."""
        input_text = "My email is willy@example.com and his is secret.agent@gmail.com"
        expected = "My email is [EMAIL_REDACTED] and his is [EMAIL_REDACTED]"
        assert mask_pii(input_text) == expected

    def test_pii_masking_no_email(self):
        """Verify that text without emails is unchanged."""
        input_text = "Hello world, how are you?"
        assert mask_pii(input_text) == input_text

    def test_callback_handler_config(self):
        """Verify that langfuse callback is initialized with correct tags."""
        settings = get_settings()
        # Mock API keys so it doesn't return None
        with (
            patch.object(settings, "LANGFUSE_PUBLIC_KEY", "pk-test"),
            patch.object(settings, "LANGFUSE_SECRET_KEY", "sk-test"),
            patch("src.core.observability.CallbackHandler") as mock_handler
        ):
            get_langfuse_callback(session_id="test-session", user_id="user-123")
            
            mock_handler.assert_called_once()
            args, kwargs = mock_handler.call_args
            
            # Check tags
            tags = kwargs.get("tags", [])
            assert settings.ENVIRONMENT in tags
            assert settings.VERSION == kwargs.get("version")
            
            # Check session/user id
            assert kwargs.get("session_id") == "test-session"
            assert kwargs.get("user_id") == "user-123"

class TestObservabilityEndpoints:
    def test_feedback_endpoint_success(self, client):
        """Verify that the feedback endpoint accepts valid requests."""
        # Need to mock the graph check for session existence
        with (
            patch("src.api.chat.Langfuse") as mock_langfuse,
            patch("src.api.chat.get_graph_instance") as mock_graph_dep
        ):
            mock_client = mock_langfuse.return_value
            mock_graph = MagicMock()
            # Mock aget_state to return a valid state so session check passes
            mock_graph.aget_state = AsyncMock(return_value=MagicMock(values={"employee_name": "Test"}))
            
            client.app.dependency_overrides[mock_graph_dep] = lambda: mock_graph
            
            response = client.post(
                "/api/v1/sessions/test-session-123/feedback",
                json={
                    "trace_id": "trace-123",
                    "score": 1,
                    "comment": "Very helpful!"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            
            # Verify langfuse client was called
            mock_client.score.assert_called_once_with(
                trace_id="trace-123",
                name="user-feedback",
                value=1,
                comment="Very helpful!"
            )

    def test_feedback_endpoint_invalid_score(self, client):
        """Verify that invalid scores are rejected."""
        response = client.post(
            "/api/v1/sessions/test-session-123/feedback",
            json={
                "score": 10, # Invalid score (not -1, 0, 1)
            }
        )
        assert response.status_code == 422

    @patch("src.api.chat._get_session_state")
    @patch("src.api.chat.get_langfuse_callback")
    def test_chat_sse_includes_trace_id(self, mock_get_callback, mock_get_state, client):
        """Verify that agent_start event in SSE includes trace_id."""
        # Mock session state
        mock_get_state.return_value = {"employee_name": "Test User"}
        
        # Mock langfuse handler with a trace_id
        mock_handler = MagicMock()
        mock_handler.trace_id = "mock-trace-id-456"
        mock_get_callback.return_value = mock_handler
        
        # Mock the graph execution to yield something
        from langchain_core.messages import AIMessage
        async def mock_stream(*args, **kwargs):
            # First yield metadata to simulate node start
            yield {"node_name": {"messages": [AIMessage(content="Hello")]}}

        with patch("src.api.chat.get_graph_instance") as mock_graph_dep:
            mock_graph = MagicMock()
            mock_graph.astream.side_effect = mock_stream
            # Mock aget_state with AsyncMock
            mock_graph.aget_state = AsyncMock(return_value=MagicMock(next=[]))
            
            client.app.dependency_overrides[mock_graph_dep] = lambda: mock_graph
            
            response = client.post(
                "/api/v1/sessions/session-789/chat",
                json={"message": "hi", "user_id": "user-789"}
            )
            
            assert response.status_code == 200
            
            # Read SSE stream
            events = []
            for line in response.iter_lines():
                line_str = line.decode('utf-8')
                if line_str.startswith("event: "):
                    events.append({"event": line_str[7:]})
                elif line_str.startswith("data: "):
                    events[-1]["data"] = json.loads(line_str[6:])
            
            # Check if agent_start has trace_id
            agent_start = next((e for e in events if e["event"] == "agent_start"), None)
            assert agent_start is not None
            assert agent_start["data"]["trace_id"] == "mock-trace-id-456"
