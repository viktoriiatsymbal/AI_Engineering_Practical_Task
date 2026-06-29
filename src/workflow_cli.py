"""
CLI that drives the unified LangGraph
"""
import json
from src.orchestration.service import build_workflow_service

def main():
    service = build_workflow_service()
    print("CityPark Stage 4 workflow. Type 'exit' to quit.")
    try:
        while True:
            message = input("you: ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            if not message:
                continue

            result = service.start(message=message)
            print(json.dumps(result, default=str, indent=2))
            if result["status"] == "waiting_for_admin":
                decision = input("administrator [approve/refuse]: ").strip().lower()
                comment = input("comment (optional): ").strip() or None
                result = service.resume_admin(
                    result["workflow_id"], decision, comment)
                print(json.dumps(result, default=str, indent=2))
    finally:
        service.close()

if __name__ == "__main__":
    main()
