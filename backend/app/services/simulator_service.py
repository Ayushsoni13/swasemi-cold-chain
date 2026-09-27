import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from app.db.session import SessionLocal
from app.models.shipment import Shipment
from app.models.tracker import Tracker
from app.models.enums import ShipmentStatusEnum
from app.services.telemetry_service import process_telemetry_payload

logger = logging.getLogger("BackgroundSimulator")

# Map of shipment.id -> current moving coordinates & telemetry parameters
SIM_TRACKER_STATES = {}

class BackgroundSimulatorService:
    def __init__(self):
        self.is_running = False
        self.task = None

    async def _simulator_loop(self):
        logger.info("Background Simulator Service started for active production shipments...")
        while self.is_running:
            try:
                db = SessionLocal()
                try:
                    # Query all active shipments in transit
                    active_shipments = db.query(Shipment).filter(
                        Shipment.status == ShipmentStatusEnum.IN_TRANSIT.value
                    ).all()

                    for shipment in active_shipments:
                        tracker = db.query(Tracker).filter(Tracker.id == shipment.tracker_id).first()
                        if not tracker:
                            continue

                        # Default coordinates if not specified
                        o_lat = shipment.origin_lat if shipment.origin_lat is not None else 23.0225
                        o_lng = shipment.origin_lng if shipment.origin_lng is not None else 72.5714
                        t_lat = shipment.target_lat if shipment.target_lat is not None else 23.2156
                        t_lng = shipment.target_lng if shipment.target_lng is not None else 72.6369

                        # Track state for smooth moving step
                        state = SIM_TRACKER_STATES.get(shipment.id)
                        if not state:
                            mid_temp = (shipment.allowed_min_temp + shipment.allowed_max_temp) / 2.0
                            state = {
                                "curr_lat": float(o_lat),
                                "curr_lng": float(o_lng),
                                "target_temp": round(mid_temp, 1),
                                "battery": 98.0
                            }
                            SIM_TRACKER_STATES[shipment.id] = state

                        # Move towards target coordinate progressively
                        lat_step = (t_lat - o_lat) * 0.005
                        lng_step = (t_lng - o_lng) * 0.005

                        state["curr_lat"] += lat_step + random.uniform(-0.00005, 0.00005)
                        state["curr_lng"] += lng_step + random.uniform(-0.00005, 0.00005)

                        # Generate slight temperature variation around target temp
                        temp_variation = random.uniform(-0.2, 0.2)
                        curr_temp = round(state["target_temp"] + temp_variation, 2)
                        state["battery"] = max(10.0, round(state["battery"] - 0.01, 1))

                        payload = {
                            "tracker_id": tracker.id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "latitude": round(state["curr_lat"], 6),
                            "longitude": round(state["curr_lng"], 6),
                            "temperature": curr_temp,
                            "humidity": round(60.0 + random.uniform(-1.5, 1.5), 1),
                            "battery_level": state["battery"],
                            "door_open": False
                        }

                        # Process telemetry payload through ingestion pipeline
                        process_telemetry_payload(db, payload)

                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Error in background simulator loop: {e}")

            await asyncio.sleep(5.0)

    def start(self, loop=None):
        self.is_running = True
        if loop is None:
            loop = asyncio.get_event_loop()
        self.task = loop.create_task(self._simulator_loop())
        logger.info("Background Simulator Service task created successfully.")

    def stop(self):
        self.is_running = False
        if self.task:
            self.task.cancel()
            logger.info("Background Simulator Service task stopped.")

background_simulator = BackgroundSimulatorService()
