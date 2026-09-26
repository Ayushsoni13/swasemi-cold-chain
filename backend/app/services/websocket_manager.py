import json
import logging
import asyncio
from typing import Dict, List, Set, Any
from fastapi import WebSocket
from app.models.enums import RoleEnum

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    def __init__(self):
        # Map organization_id -> Set of WebSockets for normal Users
        self.org_connections: Dict[str, Set[WebSocket]] = {}
        # Set of WebSockets for Super Admins
        self.super_admin_connections: Set[WebSocket] = set()
        self.main_loop = None

    def set_main_loop(self, loop):
        self.main_loop = loop

    def broadcast_from_thread(self, organization_id: str, message: Dict[str, Any]):
        if self.main_loop and self.main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_organization(organization_id, message),
                self.main_loop
            )
        else:
            try:
                loop = asyncio.get_running_loop()
                if loop and loop.is_running():
                    loop.create_task(self.broadcast_to_organization(organization_id, message))
            except RuntimeError:
                pass


    async def connect(self, websocket: WebSocket, role: str, organization_id: str = None):
        await websocket.accept()
        if role == RoleEnum.SUPER_ADMIN.value:
            self.super_admin_connections.add(websocket)
            logger.info("Super Admin WebSocket client connected.")
        elif organization_id:
            if organization_id not in self.org_connections:
                self.org_connections[organization_id] = set()
            self.org_connections[organization_id].add(websocket)
            logger.info(f"WebSocket client connected to organization '{organization_id}'.")

    def disconnect(self, websocket: WebSocket, role: str, organization_id: str = None):
        if role == RoleEnum.SUPER_ADMIN.value:
            self.super_admin_connections.discard(websocket)
            logger.info("Super Admin WebSocket client disconnected.")
        elif organization_id and organization_id in self.org_connections:
            self.org_connections[organization_id].discard(websocket)
            if not self.org_connections[organization_id]:
                del self.org_connections[organization_id]
            logger.info(f"WebSocket client disconnected from organization '{organization_id}'.")

    async def broadcast_to_organization(self, organization_id: str, message: Dict[str, Any]):
        """
        Sends telemetry message to all WebSocket connections for the target organization_id
        as well as all Super Admin WebSocket connections.
        """
        message_json = json.dumps(message) if isinstance(message, dict) else message
        
        # 1. Target Organization Clients
        org_sockets = list(self.org_connections.get(organization_id, set()))
        for ws in org_sockets:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.warning(f"Error sending to organization WS client: {e}")
                self.disconnect(ws, RoleEnum.USER.value, organization_id)

        # 2. Super Admin Clients
        super_sockets = list(self.super_admin_connections)
        for ws in super_sockets:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                logger.warning(f"Error sending to Super Admin WS client: {e}")
                self.disconnect(ws, RoleEnum.SUPER_ADMIN.value)

ws_manager = ConnectionManager()
