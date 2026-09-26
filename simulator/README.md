# SWASEMI Telemetry Simulator

Simulates real-time telemetry output (GPS coordinates, temperature, battery level) for 3 moving cold-chain trackers:
- `TRK-001` (Refrigerated Van A)
- `TRK-002` (Cold Truck B)
- `TRK-003` (Pharma Express C)

In Phase 2, this simulator connects to the EMQX public MQTT broker `broker.emqx.io:1883` on topic `swasemi/telemetry/{tracker_id}`.
