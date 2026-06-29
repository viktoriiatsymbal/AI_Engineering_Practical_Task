"""
Administrator console for the REST API
"""
import json
import httpx
from src.config import load_settings

_UNFINISHED_STATES = {"pending_admin", "awaiting_confirmation"}
_COMPLETED_STATES = {"approved", "refused"}

def _headers(settings):
    return {"Authorization": f"Bearer {settings.admin_api_token}"}

def parse_confirmation(answer):
    value = answer.strip().lower()
    if value in {"yes", "y"}:
        return "approve"
    if value in {"no", "n"}:
        return "reject"
    raise ValueError("Expected yes/y or no/n")

def parse_list_command(command):
    value = " ".join(command.strip().lower().split())
    if value in {"list", "list pending"}:
        return "pending"
    if value == "list all":
        return "all"
    return None

def filter_reviews(reviews, mode):
    if mode == "all":
        return reviews
    if mode == "pending":
        return [
            review for review in reviews
            if review.get("review_state") in _UNFINISHED_STATES]
    raise ValueError(f"Unsupported list mode: {mode}")

def _print_json(value):
    print(json.dumps(value, indent=2, default=str))

def main():
    settings = load_settings()

    with httpx.Client(
        base_url=settings.admin_api_url,
        headers=_headers(settings),
        timeout=settings.admin_api_timeout_seconds) as client:
        print("CityPark administrator console")
        print(
            "Commands: list, list pending, list all, "
            "open <reservation-id>, quit")

        while True:
            command = input("admin> ").strip()

            if not command:
                continue
            if command.lower() == "quit":
                break

            list_mode = parse_list_command(command)
            if list_mode is not None:
                response = client.get("/admin/requests")
                response.raise_for_status()
                _print_json(filter_reviews(response.json(), list_mode))
                continue

            if command.lower().startswith("open "):
                parts = command.split(maxsplit=1)
                if len(parts) != 2 or not parts[1].strip():
                    print("Usage: open <reservation-id>")
                    continue

                reservation_id = parts[1].strip()
                response = client.get(
                    f"/admin/requests/{reservation_id}")
                response.raise_for_status()
                review = response.json()
                _print_json(review)

                if review.get("review_state") in _COMPLETED_STATES:
                    print("This reservation has already been decided.")
                    continue

                instruction = input(
                    "Decision instruction "
                    "(for example: 'approve this reservation'): ").strip()
                if not instruction:
                    print("Decision instruction cannot be empty.")
                    continue

                proposed = client.post(
                    "/admin/commands",
                    json={
                        "reservation_id": reservation_id,
                        "instruction": instruction})
                proposed.raise_for_status()
                proposed_body = proposed.json()
                _print_json(proposed_body)

                if proposed_body["status"] == "awaiting_confirmation":
                    while True:
                        answer = input(
                            "Approve execution of the proposed action? "
                            "[yes/no]: ")
                        try:
                            middleware_decision = parse_confirmation(answer)
                            break
                        except ValueError:
                            print("Please enter yes/y or no/n.")

                    decided = client.post(
                        "/admin/decisions",
                        json={
                            "thread_id": proposed_body["thread_id"],
                            "decision": middleware_decision,
                            "message": (
                                None
                                if middleware_decision == "approve"
                                else "Administrator cancelled this action.")})
                    decided.raise_for_status()
                    _print_json(decided.json())
                continue

            print("Unknown command.")

if __name__ == "__main__":
    main()
