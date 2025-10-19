"""Health check router."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return service health status.

    Used by Kubernetes liveness/readiness probes and load balancers
    to verify the AI Engine is running and responsive.
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "aegis-ai-engine",
    }
