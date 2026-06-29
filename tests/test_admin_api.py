from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.admin_api import create_app

def _settings():
    return SimpleNamespace(admin_api_token="secret")

def test_admin_api_rejects_missing_token():
    database = MagicMock()
    agent = MagicMock()
    app = create_app(_settings(), database, agent)

    with TestClient(app) as client:
        response = client.get("/admin/requests")

    assert response.status_code == 401

def test_submit_request_creates_admin_review():
    database = MagicMock()
    database.get_admin_review.return_value = None
    database.create_admin_review.return_value = {
        "reservation_id": "r1",
        "thread_id": "thread-1",
        "review_state": "pending_admin"}
    agent = MagicMock()
    app = create_app(_settings(), database, agent)

    with TestClient(app) as client:
        response = client.post(
            "/admin/requests",
            headers={"Authorization": "Bearer secret"},
            json={"reservation_id": "r1"})

    assert response.status_code == 201
    database.create_admin_review.assert_called_once()
    assert response.json()["review_state"] == "pending_admin"
