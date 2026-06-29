from unittest.mock import MagicMock
import httpx
import pytest
from src.admin_client import AdminClient, AdminServiceError

def test_submit_reservation_posts_to_admin_api():
    client = AdminClient(
        "http://admin.test",
        "token")
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"review_state": "pending_admin"}
    client.client.post = MagicMock(return_value=response)

    result = client.submit_reservation("reservation-1")

    client.client.post.assert_called_once_with(
        "/admin/requests",
        json={"reservation_id": "reservation-1"})
    assert result["review_state"] == "pending_admin"

def test_submit_reservation_wraps_http_errors():
    client = AdminClient(
        "http://admin.test",
        "token")
    client.client.post = MagicMock(
        side_effect=httpx.ConnectError("offline"))

    with pytest.raises(AdminServiceError):
        client.submit_reservation("reservation-1")
