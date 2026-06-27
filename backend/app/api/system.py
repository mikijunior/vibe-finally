"""System REST endpoints (health, etc.)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Public health check endpoint.

    Returns ``{"status": "ok"}`` whenever the process is up. Suitable for
    Docker health checks and deployment probes. The legacy ``/health``
    endpoint remains available for backward compatibility.
    """
    return HealthResponse(status="ok")