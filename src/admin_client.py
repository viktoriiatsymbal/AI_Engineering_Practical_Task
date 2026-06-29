"""
REST client to escalate reservations to Stage 2
"""
import httpx

class AdminServiceError(RuntimeError):
    pass

class AdminClient:
    def __init__(self, base_url, token, timeout_seconds=10.0):
        self.client = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {token}"})

    def submit_reservation(self, reservation_id):
        try:
            response = self.client.post(
                "/admin/requests",
                json={"reservation_id": reservation_id})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise AdminServiceError(
                f"Could not escalate reservation: {exc}") from exc

    def close(self):
        self.client.close()
