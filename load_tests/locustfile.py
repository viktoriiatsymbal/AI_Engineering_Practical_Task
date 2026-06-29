"""
HTTP load scenarios for chatbot, HITL resume and status polling
"""
import os
import uuid
from locust import HttpUser, between, task

class CityParkWorkflowUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.admin_headers = {
            "Authorization": f"Bearer {os.getenv('ADMIN_API_TOKEN', 'change-me')}"}

    @task(5)
    def information_query(self):
        self.client.post(
            "/workflows",
            json={
                "workflow_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "message": "What are the parking working hours?"},
            name="workflow: information query")

    @task(1)
    def status_lookup(self):
        workflow_id = str(uuid.uuid4())
        self.client.get(
            f"/workflows/{workflow_id}",
            name="workflow: state lookup")
