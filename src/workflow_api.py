"""
REST facade for the Stage 4 LangGraph workflow
"""
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from src.orchestration.service import build_workflow_service

class WorkflowStartRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(default="default", min_length=1, max_length=255)
    workflow_id: str | None = Field(default=None, max_length=255)

class WorkflowDecisionRequest(BaseModel):
    decision: Literal["approve", "refuse"]
    comment: str | None = Field(default=None, max_length=500)

def create_app(settings=None, workflow_service=None):
    owns_service = workflow_service is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service = workflow_service or build_workflow_service(settings)
        app.state.workflow_service = service
        app.state.settings = settings or getattr(service, "settings", None)
        try:
            yield
        finally:
            if owns_service:
                service.close()

    app = FastAPI(
        title="CityPark Unified LangGraph API",
        version="4.0.0",
        lifespan=lifespan)

    def require_admin_token(request, authorization=Header(default=None)):
        resolved_settings = settings
        if resolved_settings is None:
            from src.config import load_settings

            resolved_settings = load_settings()
        expected = f"Bearer {resolved_settings.admin_api_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid administrator token")

    @app.get("/health")
    def health():
        return {"status": "ok", "stage": 4, "orchestrator": "langgraph"}

    @app.post("/workflows", status_code=status.HTTP_201_CREATED)
    def start_workflow(payload, request):
        return request.app.state.workflow_service.start(
            message=payload.message,
            session_id=payload.session_id,
            workflow_id=payload.workflow_id)

    @app.post(
        "/workflows/{workflow_id}/admin-decision",
        dependencies=[Depends(require_admin_token)])
    def resume_workflow(workflow_id, payload, request):
        try:
            return request.app.state.workflow_service.resume_admin(
                workflow_id,
                payload.decision,
                payload.comment)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/workflows/{workflow_id}/retry",
        dependencies=[Depends(require_admin_token)])
    def retry_workflow(workflow_id, request):
        return request.app.state.workflow_service.retry(workflow_id)

    @app.get("/workflows/{workflow_id}")
    def get_workflow(workflow_id, request):
        return request.app.state.workflow_service.get_state(workflow_id)

    @app.get("/workflows/{workflow_id}/history")
    def get_history(workflow_id, request):
        return request.app.state.workflow_service.get_history(workflow_id)

    return app

app = create_app()
