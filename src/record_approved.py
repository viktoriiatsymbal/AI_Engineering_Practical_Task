"""
Manual retry command for an approved reservation that was not recorded
"""
import argparse
from src.config import load_settings
from src.mcp_client import MCPReservationRecorder

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reservation_id")
    args = parser.parse_args()

    result = MCPReservationRecorder(load_settings()).record(
        args.reservation_id)
    print(result)

if __name__ == "__main__":
    main()
