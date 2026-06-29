"""
REST API and administrator interface
"""
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4
from fastapi import (
    Depends, FastAPI, Header, HTTPException, Request, status)
from pydantic import BaseModel, Field
from src.admin_agent import AdminApprovalAgent
from src.config import load_settings
from src.database import Database
from src.mcp_client import MCPReservationRecorder

class ReservationEscalationRequest(BaseModel):
    reservation_id: str

class AdminCommandRequest(BaseModel):
    reservation_id: str
    instruction: str = Field(min_length=3, max_length=500)

class HITLDecisionRequest(BaseModel):
    thread_id: str
    decision: Literal["approve", "reject"]
    message: str | None = Field(default=None, max_length=500)

def create_app(settings=None, database=None, admin_agent=None):
    owns_agent = admin_agent is None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings = settings or load_settings()
        resolved_database = database or Database(
            settings=resolved_settings)
        resolved_database.create_all()

        app.state.settings = resolved_settings
        app.state.database = resolved_database
        app.state.admin_agent = (
            admin_agent
            or AdminApprovalAgent(
                settings=resolved_settings,
                database=resolved_database,
                mcp_recorder=MCPReservationRecorder(
                    resolved_settings)))

        try:
            yield
        finally:
            if owns_agent:
                app.state.admin_agent.close()

    app = FastAPI(
        title="CityPark Administrator API",
        version="2.0.0",
        lifespan=lifespan)

    def require_token(request, authorization=Header(default=None)):
        expected = f"Bearer {request.app.state.settings.admin_api_token}"
        if authorization != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid administrator token")

    @app.get("/health")
    def health():
        return {"status": "ok", "stage": 3}

    @app.post(
        "/admin/requests",
        dependencies=[Depends(require_token)],
        status_code=status.HTTP_201_CREATED)
    def submit_request(payload, request):
        database = request.app.state.database
        try:
            existing = database.get_admin_review(
                payload.reservation_id)
            if existing is not None:
                return existing

            return database.create_admin_review(
                reservation_id=payload.reservation_id,
                thread_id=str(uuid4()))
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc)) from exc

    @app.get(
        "/admin/requests",
        dependencies=[Depends(require_token)])
    def list_requests(request, review_state=None):
        return request.app.state.database.list_admin_reviews(
            state=review_state)

    @app.get(
        "/admin/requests/{reservation_id}",
        dependencies=[Depends(require_token)])
    def get_request(reservation_id: str, request: Request):
        review = request.app.state.database.get_admin_review(
            reservation_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation review not found")
        return review

    @app.post(
        "/admin/commands",
        dependencies=[Depends(require_token)])
    def propose_action(payload, request):
        database = request.app.state.database
        review = database.get_admin_review(payload.reservation_id)
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation review not found")

        try:
            return request.app.state.admin_agent.propose(
                reservation_id=payload.reservation_id,
                instruction=payload.instruction,
                thread_id=review["thread_id"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)) from exc

    @app.post(
        "/admin/decisions",
        dependencies=[Depends(require_token)])
    def review_action(payload, request):
        try:
            result = request.app.state.admin_agent.resume(
                thread_id=payload.thread_id,
                decision=payload.decision,
                message=payload.message)
            return result
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)) from exc

    return app

app = create_app()
