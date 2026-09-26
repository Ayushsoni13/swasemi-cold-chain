import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.models.enums import RoleEnum
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("WebSocketAPI")
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None)
):
    if not token:
        logger.warning("WebSocket connection rejected: Missing token query parameter")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if not payload:
        logger.warning("WebSocket connection rejected: Invalid or expired JWT token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload.get("sub")
    role = payload.get("role")
    organization_id = payload.get("organization_id")

    # Verify user in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("WebSocket connection rejected: User not found in database")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Enforce organization isolation from JWT/User DB
        effective_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        effective_org_id = user.organization_id if effective_role != RoleEnum.SUPER_ADMIN.value else None
    finally:
        db.close()

    await ws_manager.connect(websocket, role=effective_role, organization_id=effective_org_id)

    try:
        while True:
            # Receive client messages or pings
            data = await websocket.receive_text()
            logger.debug(f"Received WS text message from user {user_id}: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, role=effective_role, organization_id=effective_org_id)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket, role=effective_role, organization_id=effective_org_id)
