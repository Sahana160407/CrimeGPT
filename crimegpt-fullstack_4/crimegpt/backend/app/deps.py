from fastapi import Header, HTTPException

from app.security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

    return payload  # {id, username, role, name, officeLocation}
