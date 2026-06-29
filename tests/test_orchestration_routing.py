from src.orchestration.routing import route_after_user_interaction

def test_routes_new_reservation_to_admin_review():
    state = {"reservation_id": "r-1"}
    assert route_after_user_interaction(state) == "submit_admin_review"

def test_routes_information_response_to_finalize():
    assert route_after_user_interaction({}) == "finalize"
