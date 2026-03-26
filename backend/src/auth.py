from fastapi import Header, HTTPException, status
from typing import Optional

# ─── Simple token auth (no Firebase) ───────────────────────────────────────────
# The frontend stores the token in localStorage and sends it as Bearer <token>.
# For the test login, the token is "dummy_token".
# In production, replace this with a proper JWT verification.

VALID_TOKENS = {
    "dummy_token": "admin_test_user",
}


async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency to verify API tokens.
    Accepts any token registered in VALID_TOKENS.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()

    user_id = VALID_TOKENS.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
