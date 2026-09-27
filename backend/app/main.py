import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router
from app.api.health import health_check
from app.api.auth import router as auth_router
from app.api.trackers import router as trackers_router
from app.api.shipments import router as shipments_router
from app.api.alerts import router as alerts_router
from app.api.websocket import router as websocket_router
from app.services.mqtt_service import mqtt_service
from app.services.redis_listener import redis_listener
from app.services.simulator_service import background_simulator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Register main asyncio loop for background thread WS broadcasts
    from app.services.websocket_manager import ws_manager
    ws_manager.set_main_loop(asyncio.get_running_loop())

    # Start MQTT Subscriber, Redis Listener & Background Simulator services
    try:
        mqtt_service.start()
    except Exception as e:
        print(f"Warning: Could not start MQTT subscriber service: {e}")
        
    try:
        redis_listener.start(loop=asyncio.get_running_loop())
    except Exception as e:
        print(f"Warning: Could not start Redis listener service: {e}")

    try:
        background_simulator.start(loop=asyncio.get_running_loop())
    except Exception as e:
        print(f"Warning: Could not start background simulator service: {e}")

    yield

    # Shutdown
    try:
        background_simulator.stop()
    except Exception as e:
        print(f"Error stopping background simulator service: {e}")

    try:
        mqtt_service.stop()
    except Exception as e:
        print(f"Error stopping MQTT subscriber service: {e}")
        
    try:
        redis_listener.stop()
    except Exception as e:
        print(f"Error stopping Redis listener service: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="SWASEMI Cold-Chain Monitoring Platform Backend API",
    lifespan=lifespan
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root health check routes
app.add_api_route("/health", health_check, methods=["GET"], tags=["Health"])
app.add_api_route("/healthz", health_check, methods=["GET"], tags=["Health"])

from app.api.organizations import router as organizations_router
from app.api.users import router as users_router

# Direct top-level route aliases
app.include_router(auth_router, prefix="/auth", tags=["Auth Direct"])
app.include_router(organizations_router, prefix="/organizations", tags=["Organizations Direct"])
app.include_router(users_router, prefix="/users", tags=["Users Direct"])
app.include_router(trackers_router, prefix="/trackers", tags=["Trackers Direct"])
app.include_router(shipments_router, prefix="/shipments", tags=["Shipments Direct"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts Direct"])
app.include_router(websocket_router, tags=["WebSocket Direct"])


# API v1 versioned routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to SWASEMI Cold-Chain Monitoring Platform API",
        "docs": "/docs",
        "health": "/health"
    }
