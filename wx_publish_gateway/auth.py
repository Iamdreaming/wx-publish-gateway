"""API key authentication for wx-publish-gateway."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException


def verify_api_key(valid_keys: list[str]):
    """Return a FastAPI dependency that validates the X-API-Key header."""

    def _dep(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
        if not x_api_key or x_api_key not in valid_keys:
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing X-API-Key. Provide a valid API key in the X-API-Key header.",
            )

    return Depends(_dep)
