"""
Application service and dependency wiring for the graph
"""
from contextlib import ExitStack
from uuid import uuid4
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from src.admin_agent import AdminApprovalAgent
from src.chatbot import ParkingChatbot
from src.config import load_settings
from src.database import Database
from src.guardrails import GuardRails
from src.mcp_client import MCPReservationRecorder
from src.orchestration.graph import build_workflow_graph
from src.orchestration.nodes import OrchestrationNodes
from src.rag_chain import RAGChain
from src.vector_store import StaticKnowledgeBase, connect

class ParkingWorkflowService:
    def __init__(self, graph, resources=None):
        self.graph = graph
        self._resources = resources

    @staticmethod
    def config(workflow_id):
        return {
            "configurable": {"thread_id": workflow_id},
            "recursion_limit": 20}

    def start(self, message, session_id="default", workflow_id=None):
        workflow_id = workflow_id or str(uuid4())
        result = self.graph.invoke(
            {
                "workflow_id": workflow_id,
                "session_id": session_id,
                "user_message": message},
            config=self.config(workflow_id),
            durability="sync")
        return self._response(workflow_id, result)

    def resume_admin(self, workflow_id, decision, comment=None):
        result = self.graph.invoke(
            Command(
                resume={
                    "decision": decision,
                    "comment": comment}),
            config=self.config(workflow_id),
            durability="sync")
        return self._response(workflow_id, result)

    def retry(self, workflow_id):
        result = self.graph.invoke(
            None,
            config=self.config(workflow_id),
            durability="sync")
        return self._response(workflow_id, result)

    def get_state(self, workflow_id):
        snapshot = self.graph.get_state(self.config(workflow_id))
        return {
            "workflow_id": workflow_id,
            "values": dict(snapshot.values),
            "next": list(snapshot.next),
            "created_at": snapshot.created_at,
            "interrupts": [
                interrupt.value
                for task in snapshot.tasks
                for interrupt in task.interrupts]}

    def get_history(self, workflow_id):
        return [
            {
                "values": dict(snapshot.values),
                "next": list(snapshot.next),
                "created_at": snapshot.created_at,
                "step": snapshot.metadata.get("step")}
            for snapshot in self.graph.get_state_history(
                self.config(workflow_id))]

    @staticmethod
    def _response(workflow_id, result):
        interrupts = result.get("__interrupt__", ())
        return {
            "workflow_id": workflow_id,
            "status": (
                "waiting_for_admin"
                if interrupts
                else result.get("workflow_status", "completed")),
            "response": result.get("final_response")
            or result.get("assistant_response"),
            "reservation_id": result.get("reservation_id"),
            "interrupts": [item.value for item in interrupts],
            "state": result}

    def close(self):
        if self._resources is not None:
            self._resources.close()
            self._resources = None

def build_workflow_service(settings=None):
    """Wire real Stage 1-3 services into the parent LangGraph."""
    settings = settings or load_settings()
    resources = ExitStack()

    database = Database(settings=settings)
    database.create_all()
    vector_client = connect(settings)
    resources.callback(vector_client.close)

    guardrails = GuardRails()
    knowledge_base = StaticKnowledgeBase(vector_client, settings)
    rag = RAGChain(settings, knowledge_base, database, guardrails)
    chatbot = ParkingChatbot(
        settings,
        rag,
        database,
        guardrails,
        admin_client=None)
    resources.callback(chatbot.close)

    checkpointer_cm = PostgresSaver.from_conn_string(
        settings.postgres_checkpoint_dsn)
    checkpointer = resources.enter_context(checkpointer_cm)
    checkpointer.setup()

    admin_agent = AdminApprovalAgent(
        settings=settings,
        database=database)
    resources.callback(admin_agent.close)
    recorder = MCPReservationRecorder(settings)

    graph = build_workflow_graph(
        OrchestrationNodes(
            chatbot=chatbot,
            database=database,
            admin_agent=admin_agent,
            mcp_recorder=recorder),
        checkpointer=checkpointer)
    return ParkingWorkflowService(graph, resources=resources)

def make_graph():
    """Factory referenced by langgraph.json for LangGraph deployments."""
    return build_workflow_service().graph
