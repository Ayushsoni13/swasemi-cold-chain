from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/health", summary="Health check")
@router.get("/healthz", summary="Healthz check")
def health_check():
    return {
        "status": "ok",
        "service": "SWASEMI Cold-Chain Monitoring API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
