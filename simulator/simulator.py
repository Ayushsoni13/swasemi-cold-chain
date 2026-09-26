import time
import json
import random
import logging
import argparse
import os
import sqlite3
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SWASEMISimulator")

# Configuration
BROKER = "broker.emqx.io"
PORT = 1883
INTERVAL = 5.0  # seconds

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "swasemi_coldchain.db")

DYNAMIC_TRACKERS = {}

INDIAN_CITIES = [
    {"start": {"lat": 12.9716, "lng": 77.5946}, "target": {"lat": 13.0827, "lng": 80.2707}},  # Bengaluru -> Chennai
    {"start": {"lat": 19.0760, "lng": 72.8777}, "target": {"lat": 18.5204, "lng": 73.8567}},  # Mumbai -> Pune
    {"start": {"lat": 28.7041, "lng": 77.1025}, "target": {"lat": 26.9124, "lng": 75.7873}},  # Delhi -> Jaipur
    {"start": {"lat": 17.3850, "lng": 78.4867}, "target": {"lat": 16.5062, "lng": 80.6480}},  # Hyderabad -> Vijayawada
    {"start": {"lat": 22.5726, "lng": 88.3639}, "target": {"lat": 20.2961, "lng": 85.8245}},  # Kolkata -> Bhubaneswar
]

# Fallback default trackers
DEFAULT_TRACKERS = [
    {
        "tracker_id": "TRK-001",
        "name": "Refrigerated Van A",
        "mqtt_topic": "swasemi/coldchain/trackers/TRK-001",
        "route_start": {"lat": 12.9716, "lng": 77.5946},
        "current": {"lat": 12.9716, "lng": 77.5946},
        "target": {"lat": 13.0827, "lng": 80.2707},
        "target_temp": 4.0,
        "humidity": 65.0,
        "battery": 98.0,
        "door_open": False
    },
    {
        "tracker_id": "TRK-002",
        "name": "Cold Truck B",
        "mqtt_topic": "swasemi/coldchain/trackers/TRK-002",
        "route_start": {"lat": 19.0760, "lng": 72.8777},
        "current": {"lat": 19.0760, "lng": 72.8777},
        "target": {"lat": 18.5204, "lng": 73.8567},
        "target_temp": 5.0,
        "humidity": 60.0,
        "battery": 95.0,
        "door_open": False
    },
    {
        "tracker_id": "TRK-003",
        "name": "Pharma Express C",
        "mqtt_topic": "swasemi/coldchain/trackers/TRK-003",
        "route_start": {"lat": 28.7041, "lng": 77.1025},
        "current": {"lat": 28.7041, "lng": 77.1025},
        "target": {"lat": 26.9124, "lng": 75.7873},
        "target_temp": 3.5,
        "humidity": 70.0,
        "battery": 92.0,
        "door_open": False
    }
]
TRACKERS = DEFAULT_TRACKERS

def sync_trackers_from_db():
    """Syncs trackers from backend SQLite database so newly created trucks are automatically simulated."""
    # Ensure default trackers exist
    for trk in DEFAULT_TRACKERS:
        if trk["tracker_id"] not in DYNAMIC_TRACKERS:
            DYNAMIC_TRACKERS[trk["tracker_id"]] = dict(trk)

    db_file = os.path.abspath(DB_PATH)
    if not os.path.exists(db_file):
        return

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, mqtt_topic FROM trackers")
        rows = cursor.fetchall()
        conn.close()

        # Remove deleted trackers from dynamic list
        existing_db_ids = {row[0] for row in rows}
        for trk_id in list(DYNAMIC_TRACKERS.keys()):
            if trk_id not in existing_db_ids and trk_id not in [t["tracker_id"] for t in DEFAULT_TRACKERS]:
                del DYNAMIC_TRACKERS[trk_id]

        for idx, row in enumerate(rows):
            trk_id, trk_name, trk_topic = row[0], row[1], row[2]
            if trk_id not in DYNAMIC_TRACKERS:
                city = INDIAN_CITIES[idx % len(INDIAN_CITIES)]
                DYNAMIC_TRACKERS[trk_id] = {
                    "tracker_id": trk_id,
                    "name": trk_name,
                    "mqtt_topic": trk_topic or f"swasemi/coldchain/trackers/{trk_id}",
                    "route_start": dict(city["start"]),
                    "current": dict(city["start"]),
                    "target": dict(city["target"]),
                    "target_temp": round(random.uniform(3.0, 6.0), 1),
                    "humidity": round(random.uniform(60.0, 75.0), 1),
                    "battery": round(random.uniform(90.0, 100.0), 1),
                    "door_open": False
                }
                logger.info(f"Discovered new tracker from DB: '{trk_id}' ({trk_name}) on topic '{trk_topic}'")

        # Check active shipments for custom route coordinates (e.g. Ahmedabad -> Gandhinagar)
        cursor.execute("SELECT id, tracker_id, origin_lat, origin_lng, target_lat, target_lng FROM shipments WHERE status = 'IN_TRANSIT'")
        shipment_rows = cursor.fetchall()

        for s_row in shipment_rows:
            s_id, s_trk_id, o_lat, o_lng, t_lat, t_lng = s_row
            if s_trk_id in DYNAMIC_TRACKERS and o_lat is not None and t_lat is not None:
                trk = DYNAMIC_TRACKERS[s_trk_id]
                if trk.get("active_shipment_id") != s_id:
                    trk["active_shipment_id"] = s_id
                    trk["route_start"] = {"lat": float(o_lat), "lng": float(o_lng)}
                    trk["current"] = {"lat": float(o_lat), "lng": float(o_lng)}
                    trk["target"] = {"lat": float(t_lat), "lng": float(t_lng)}
                    logger.info(f"Updated tracker '{s_trk_id}' route for shipment '{s_id}': ({o_lat}, {o_lng}) -> ({t_lat}, {t_lng})")
    except Exception as e:
        logger.debug(f"DB sync check: {e}")

def generate_telemetry(tracker, breach_mode: bool = False):
    """Generates next GPS position and telemetry for tracker."""
    lat_step = (tracker["target"]["lat"] - tracker["route_start"]["lat"]) * 0.0005
    lng_step = (tracker["target"]["lng"] - tracker["route_start"]["lng"]) * 0.0005

    tracker["current"]["lat"] += lat_step + random.uniform(-0.0001, 0.0001)
    tracker["current"]["lng"] += lng_step + random.uniform(-0.0001, 0.0001)

    if breach_mode and tracker["tracker_id"] == "TRK-001":
        current_temp = round(9.5 + random.uniform(0.1, 1.5), 2)
    else:
        temp_var = random.uniform(-0.3, 0.3)
        current_temp = round(tracker["target_temp"] + temp_var, 2)

    tracker["battery"] = max(1.0, round(tracker["battery"] - 0.01, 2))

    return {
        "tracker_id": tracker["tracker_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": round(tracker["current"]["lat"], 6),
        "longitude": round(tracker["current"]["lng"], 6),
        "temperature": current_temp,
        "humidity": round(tracker["humidity"] + random.uniform(-1.0, 1.0), 1),
        "battery_level": tracker["battery"],
        "door_open": tracker["door_open"]
    }

def main():
    parser = argparse.ArgumentParser(description="SWASEMI Telemetry Simulator")
    parser.add_argument("--breach", action="store_true", help="Simulate temperature breach (> 8°C) for TRK-001")
    parser.add_argument("--once", action="store_true", help="Publish one batch of messages and exit")
    args = parser.parse_args()

    logger.info("Initializing SWASEMI Telemetry Simulator...")
    logger.info(f"Target MQTT Broker: {BROKER}:{PORT}")
    
    sync_trackers_from_db()
    logger.info(f"Active trackers list: {list(DYNAMIC_TRACKERS.keys())}")
    
    if args.breach:
        logger.warning("Simulating Temperature Breach mode for TRK-001 (>8.0°C)")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()
        logger.info("Connected to MQTT broker successfully.")
    except Exception as e:
        logger.error(f"Could not connect to MQTT broker: {e}")
        return

    try:
        while True:
            sync_trackers_from_db()
            active_list = list(DYNAMIC_TRACKERS.values())
            for tracker in active_list:
                payload = generate_telemetry(tracker, breach_mode=args.breach)
                topic = tracker.get("mqtt_topic") or f"swasemi/coldchain/trackers/{tracker['tracker_id']}"
                payload_json = json.dumps(payload)
                
                client.publish(topic, payload_json)
                logger.info(f"Published to '{topic}': Temp={payload['temperature']}°C, Lat={payload['latitude']}, Lng={payload['longitude']}")

            if args.once:
                break
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Simulator stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
