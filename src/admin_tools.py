"""
LangChain tools for administrator agent
"""
import json
from langchain.tools import tool

def build_admin_tools(database):
    @tool
    def get_reservation_details(reservation_id):
        """Read one reservation and its current review status."""
        review = database.get_admin_review(reservation_id)
        if review is None:
            return json.dumps(
                {"error": "Reservation review was not found"})
        return json.dumps(review, default=str)

    @tool
    def approve_reservation(reservation_id, comment=""):
        """Approve a pending parking reservation after human confirmation."""
        result = database.resolve_admin_review(
            reservation_id=reservation_id,
            decision="approved",
            comment=comment or None)
        return json.dumps(result, default=str)

    @tool
    def refuse_reservation(reservation_id, comment=""):
        """Refuse a pending parking reservation after human confirmation."""
        result = database.resolve_admin_review(
            reservation_id=reservation_id,
            decision="refused",
            comment=comment or None)
        return json.dumps(result, default=str)

    return [
        get_reservation_details,
        approve_reservation,
        refuse_reservation]
