"""
FastMCP server for reservation recording
"""
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from src.approved_reservation_store import ApprovedReservationStore
from src.config import load_settings
from src.database import Database

def build_mcp_server(settings=None, database=None, store=None):
    settings = settings or load_settings()
    database = database or Database(settings=settings)
    database.create_all()
    store = store or ApprovedReservationStore(
        output_file=settings.mcp_output_file,
        index_file=settings.mcp_index_file)

    verifier = JWTVerifier(
        public_key=settings.mcp_jwt_secret,
        issuer=settings.mcp_jwt_issuer,
        audience=settings.mcp_jwt_audience,
        algorithm="HS256",
        required_scopes=["reservations:write"])

    server = FastMCP(
        name="CityPark Reservation Storage",
        instructions=(
            "Records only administrator-approved parking reservations "
            "in the required text-file format."),
        auth=verifier)

    @server.tool()
    def record_approved_reservation(reservation_id):
        """Record an approved reservation in durable text-file storage."""
        review = database.get_admin_review(reservation_id)
        if review is None:
            raise ValueError("Reservation review was not found")
        if review["review_state"] != "approved":
            raise PermissionError(
                "Only administrator-approved reservations may be recorded")
        if review["decided_at"] is None:
            raise ValueError("Approved reservation has no approval timestamp")

        return store.record(
            reservation_id=reservation_id,
            reservation=review["reservation"],
            approval_time=review["decided_at"])

    return server

if __name__ == "__main__":
    settings = load_settings()
    mcp = build_mcp_server(settings=settings)
    mcp.run(
        transport="http",
        host=settings.mcp_host,
        port=settings.mcp_port)
