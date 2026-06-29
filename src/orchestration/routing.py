"""
Routing functions for the graph
"""

def route_after_user_interaction(state):
    """Only newly-created reservations enter the approval pipeline."""
    return "submit_admin_review" if state.get("reservation_id") else "finalize"
