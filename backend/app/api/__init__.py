from fastapi import APIRouter
from app.api import health, auth, trackers, shipments, alerts, websocket

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(trackers.router, prefix="/trackers", tags=["Trackers"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["Shipments"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(websocket.router, tags=["WebSocket"])
