from types import SimpleNamespace
from unittest.mock import Mock
from fastapi.testclient import TestClient
from src.workflow_api import create_app

def settings():
    return SimpleNamespace(admin_api_token="secret")

def test_start_workflow_endpoint_calls_unified_service():
    service = Mock()
    service.start.return_value = {"workflow_id": "w-1", "status": "completed"}

    with TestClient(create_app(settings(), service)) as client:
        response = client.post(
            "/workflows",
            json={"message": "Where is the parking?", "session_id": "s-1"})

    assert response.status_code == 201
    service.start.assert_called_once()


def test_admin_decision_requires_bearer_token():
    service = Mock()
    with TestClient(create_app(settings(), service)) as client:
        response = client.post(
            "/workflows/w-1/admin-decision",
            json={"decision": "approve"})

    assert response.status_code == 401
