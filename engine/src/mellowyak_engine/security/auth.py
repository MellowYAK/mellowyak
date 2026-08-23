from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status


class SessionTokenGuard:
    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token

    def __call__(self, authorization: str | None = Header(default=None)) -> None:
        prefix = "Bearer "
        supplied = (
            authorization[len(prefix) :]
            if authorization and authorization.startswith(prefix)
            else ""
        )
        if not supplied or not hmac.compare_digest(supplied, self._expected_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LOCAL_SESSION_TOKEN_REQUIRED",
            )
