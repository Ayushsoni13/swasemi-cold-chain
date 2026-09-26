import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import type { Tracker, Shipment, WSTelemetryEvent } from '../types';
import 'leaflet/dist/leaflet.css';

// Custom Leaflet Marker Icons based on tracker status
const createCustomIcon = (status: string, isBreach: boolean = false) => {
  let color = '#10b981'; // ONLINE (emerald)
  if (status === 'DELAYED') color = '#f59e0b'; // DELAYED (amber)
  if (status === 'OFFLINE' || isBreach) color = '#f43f5e'; // OFFLINE or BREACH (rose)

  const svgMarker = `
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="18" cy="18" r="14" fill="${color}" fill-opacity="0.3" stroke="${color}" stroke-width="2"/>
      <circle cx="18" cy="18" r="7" fill="${color}"/>
    </svg>
  `;

  return L.divIcon({
    html: svgMarker,
    className: 'custom-leaflet-marker',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18]
  });
};

interface TrackerMapProps {
  trackers: Tracker[];
  shipments?: Shipment[];
  latestTelemetry: Record<string, WSTelemetryEvent>;
}

export const TrackerMap: React.FC<TrackerMapProps> = ({ trackers, shipments = [], latestTelemetry }) => {
  const [trackHistory, setTrackHistory] = useState<Record<string, [number, number][]>>({});

  // Accumulate historical coordinates for drawing live polyline trail
  React.useEffect(() => {
    setTrackHistory((prev) => {
      const nextState = { ...prev };
      trackers.forEach((t) => {
        const telemetry = latestTelemetry[t.id];
        if (telemetry && telemetry.latitude && telemetry.longitude) {
          const point: [number, number] = [telemetry.latitude, telemetry.longitude];
          const existing = nextState[t.id] || [];
          const lastPoint = existing[existing.length - 1];
          if (!lastPoint || lastPoint[0] !== point[0] || lastPoint[1] !== point[1]) {
            nextState[t.id] = [...existing.slice(-50), point]; // Keep last 50 waypoints
          }
        }
      });
      return nextState;
    });
  }, [latestTelemetry, trackers]);

  const defaultCenter: [number, number] = [20.5937, 78.9629];
  const defaultZoom = 5;

  return (
    <div style={{ height: '460px', width: '100%', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--border-color)', position: 'relative' }}>
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        style={{ height: '100%', width: '100%', background: '#0b0f19' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {trackers.map((tracker) => {
          const telemetry = latestTelemetry[tracker.id];
          
          let lat = 12.9716;
          let lng = 77.5946;

          if (tracker.id === 'TRK-002') { lat = 19.0760; lng = 72.8777; }
          if (tracker.id === 'TRK-003') { lat = 28.7041; lng = 77.1025; }

          if (telemetry) {
            lat = telemetry.latitude;
            lng = telemetry.longitude;
          }

          const activeShipment = shipments.find((s) => s.tracker_id === tracker.id && s.status === 'IN_TRANSIT');
          const currentStatus = telemetry ? telemetry.status : tracker.status;
          const isBreach = activeShipment?.breach_active || false;

          // Route Polyline points
          const historyTrail = trackHistory[tracker.id] || [];
          const polylinePoints: [number, number][] = [];

          if (activeShipment?.origin_lat && activeShipment?.origin_lng) {
            polylinePoints.push([activeShipment.origin_lat, activeShipment.origin_lng]);
          }
          historyTrail.forEach((pt) => polylinePoints.push(pt));
          polylinePoints.push([lat, lng]);
          if (activeShipment?.target_lat && activeShipment?.target_lng) {
            polylinePoints.push([activeShipment.target_lat, activeShipment.target_lng]);
          }

          return (
            <React.Fragment key={tracker.id}>
              {/* Draw Live GPS Route Trail */}
              {polylinePoints.length >= 2 && (
                <Polyline
                  positions={polylinePoints}
                  color={isBreach ? '#f43f5e' : '#0284c7'}
                  weight={4}
                  opacity={0.8}
                  dashArray={activeShipment ? undefined : '6 6'}
                />
              )}

              {/* Moving Vehicle Marker */}
              <Marker
                position={[lat, lng]}
                icon={createCustomIcon(currentStatus, isBreach)}
              >
                <Popup>
                  <div style={{ padding: '6px', fontFamily: 'var(--font-sans)', color: '#0f172a', minWidth: '220px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <h4 style={{ margin: 0, fontSize: '1rem', color: '#0284c7', fontWeight: 800 }}>
                        {tracker.name}
                      </h4>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: currentStatus === 'ONLINE' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)', color: currentStatus === 'ONLINE' ? '#059669' : '#d97706' }}>
                        {currentStatus}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.825rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {activeShipment?.route_name && (
                        <div style={{ fontWeight: 700, color: '#f97316' }}>
                          Route: {activeShipment.route_name}
                        </div>
                      )}
                      <div><strong>Tracker ID:</strong> {tracker.id}</div>
                      <div><strong>Organization:</strong> {tracker.organization_id}</div>
                      <div><strong>Temperature:</strong> <span style={{ fontWeight: 700, color: isBreach ? '#e11d48' : '#0284c7' }}>{telemetry ? `${telemetry.temperature}°C` : '4.2°C'}</span></div>
                      <div><strong>Humidity:</strong> {telemetry?.humidity ? `${telemetry.humidity}%` : '55.0%'}</div>
                      <div><strong>Battery:</strong> {telemetry?.battery_level ? `${telemetry.battery_level}%` : '98%'}</div>
                      <div><strong>Door Sensor:</strong> {telemetry ? (telemetry.door_open ? '⚠️ OPEN' : '🔒 CLOSED') : '🔒 CLOSED'}</div>

                      <div><strong>Active Shipment:</strong> {telemetry?.shipment_id || activeShipment?.id || 'None'}</div>

                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '6px', borderTop: '1px solid #e2e8f0', paddingTop: '4px' }}>
                        <strong>Live GPS:</strong> {lat.toFixed(4)}° N, {lng.toFixed(4)}° E
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}
      </MapContainer>
    </div>
  );
};

export default TrackerMap;
