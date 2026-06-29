"""
Generate a short-lived JWT for the authenticated MCP client
"""
from datetime import datetime, timedelta, timezone
import jwt
from src.config import load_settings

def create_mcp_access_token(settings=None, lifetime_minutes=480):
    settings = settings or load_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "citypark-admin-service",
        "iss": settings.mcp_jwt_issuer,
        "aud": settings.mcp_jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=lifetime_minutes),
        "scope": "reservations:write",
        "scopes": ["reservations:write"]}
    return jwt.encode(payload, settings.mcp_jwt_secret, algorithm="HS256")

if __name__ == "__main__":
    print(create_mcp_access_token())
