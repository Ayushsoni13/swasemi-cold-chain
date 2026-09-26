import json
import logging
import asyncio
from app.services.redis_service import redis_service
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("RedisListener")

class RedisListenerService:
    def __init__(self):
        self.is_running = False
        self.task = None

    async def _listen_loop(self):
        logger.info("Starting Redis PubSub listener for WebSocket fanout...")
        pubsub = redis_service.get_pubsub()
        if not pubsub:
            logger.warning("Redis PubSub not available. Real-time updates will use direct internal fanout.")
            return

        try:
            pubsub.psubscribe("telemetry:organization:*")
            logger.info("Subscribed to Redis pattern 'telemetry:organization:*'")
            
            while self.is_running:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "pmessage":
                    try:
                        channel = message.get("channel", "")
                        # Channel format: telemetry:organization:{org_id}
                        parts = channel.split(":")
                        org_id = parts[-1] if len(parts) >= 3 else ""
                        
                        data_str = message.get("data")
                        if data_str and org_id:
                            data_dict = json.loads(data_str)
                            await ws_manager.broadcast_to_organization(org_id, data_dict)
                    except Exception as e:
                        logger.warning(f"Error handling Redis message: {e}")
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.warning(f"Redis PubSub listener stopped: {e}")
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    def start(self, loop=None):
        self.is_running = True
        if loop is None:
            loop = asyncio.get_event_loop()
        self.task = loop.create_task(self._listen_loop())
        logger.info("Redis PubSub listener task created.")

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            logger.info("Redis PubSub listener task cancelled.")

redis_listener = RedisListenerService()
