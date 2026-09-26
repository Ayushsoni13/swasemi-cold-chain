import logging
import paho.mqtt.client as mqtt
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.telemetry_service import process_telemetry_payload

logger = logging.getLogger("MQTTSubscriber")

class MQTTService:
    def __init__(self):
        self.client = None
        self.broker = settings.MQTT_BROKER
        self.port = settings.MQTT_PORT
        # Phase 4 Topic format: swasemi/coldchain/trackers/{tracker_id}
        self.topics = [
            "swasemi/#",
            "swasemi/coldchain/trackers/+",
            "swasemi/telemetry/+"
        ]

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            for topic in self.topics:
                client.subscribe(topic)
                logger.info(f"Subscribed to MQTT topic: '{topic}'")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            logger.debug(f"Received MQTT message on topic '{msg.topic}'")
            db = SessionLocal()
            try:
                process_telemetry_payload(db, msg.payload)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error processing MQTT message on topic '{msg.topic}': {e}")

    def start(self):
        try:
            # Use CallbackAPIVersion.VERSION2 for paho-mqtt 2.x
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("MQTT Service background loop started.")
        except Exception as e:
            logger.error(f"Could not start MQTT client: {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT Service stopped.")

mqtt_service = MQTTService()
