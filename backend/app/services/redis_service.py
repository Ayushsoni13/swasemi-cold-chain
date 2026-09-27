import json
import logging
import time
import redis
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger("RedisService")

class RedisService:
    def __init__(self):
        self.redis_client = None
        self._last_failed_at = 0
        self._init_client()

    def _init_client(self):
        # Cooldown: Don't re-attempt connection if failed within last 10 seconds
        if time.time() - self._last_failed_at < 10:
            return

        try:
            self.redis_client = redis.Redis.from_url(
                settings.redis_connection_url,
                decode_responses=True,
                socket_connect_timeout=0.2,
                socket_timeout=0.2
            )
            self.redis_client.ping()
            logger.info(f"Initialized Redis client targeting {settings.redis_connection_url}")
        except Exception:
            logger.info(f"External Redis not detected at {settings.redis_connection_url}. In-memory PubSub fallback active for WebSockets.")
            self.redis_client = None
            self._last_failed_at = time.time()


    def publish_telemetry(self, organization_id: str, telemetry_data: Dict[str, Any]) -> bool:
        """
        Publishes stored telemetry to an organization-specific Redis channel:
        telemetry:organization:{organization_id}
        """
        channel = f"telemetry:organization:{organization_id}"
        message_json = json.dumps(telemetry_data)
        
        try:
            if not self.redis_client:
                self._init_client()
                
            if self.redis_client:
                self.redis_client.publish(channel, message_json)
                logger.debug(f"Published telemetry to Redis channel '{channel}'")
                return True
        except Exception as e:
            logger.warning(f"Redis publish failed for channel '{channel}': {e}")
            self.redis_client = None
            self._last_failed_at = time.time()
            
        return False

    def get_pubsub(self):
        """Returns a Redis PubSub instance if available."""
        try:
            if not self.redis_client:
                self._init_client()
            if self.redis_client:
                return self.redis_client.pubsub()
        except Exception as e:
            logger.warning(f"Failed to get Redis PubSub instance: {e}")
            self.redis_client = None
            self._last_failed_at = time.time()
        return None

redis_service = RedisService()
