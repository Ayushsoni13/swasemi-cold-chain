import React, { useState, useEffect } from 'react';
import { X, Download, Thermometer, MapPin, Calendar, Clock, ShieldAlert } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from 'recharts';
import { MapContainer, TileLayer, Polyline, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Shipment, TelemetryReading } from '../types';
import { fetchShipmentTelemetryApi, exportShipmentCsvApi } from '../services/api';

interface ShipmentHistoryModalProps {
  shipment: Shipment;
  onClose: () => void;
}

// Marker icon generator for route start and end
const createPointIcon = (color: string) => {
  const svgMarker = `
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="12" fill="${color}" fill-opacity="0.3" stroke="${color}" stroke-width="2"/>
      <circle cx="16" cy="16" r="6" fill="${color}"/>
    </svg>
  `;

  return L.divIcon({
    html: svgMarker,
    className: 'custom-history-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
  });
};

export const ShipmentHistoryModal: React.FC<ShipmentHistoryModalProps> = ({ shipment, onClose }) => {
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<boolean>(false);

  useEffect(() => {
    async function loadTelemetry() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchShipmentTelemetryApi(shipment.id);
        setTelemetry(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load telemetry history');
      } finally {
        setLoading(false);
      }
    }
    loadTelemetry();
  }, [shipment.id]);

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      await exportShipmentCsvApi(shipment.id);
    } catch (err: any) {
      alert(err.message || 'CSV export failed');
    } finally {
      setExporting(false);
    }
  };

  // Format telemetry for Recharts
  const chartData = telemetry.map((t) => ({
    timestamp: new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    fullTime: new Date(t.timestamp).toLocaleString(),
    temperature: t.temperature,
    humidity: t.humidity ?? 0,
    allowedMin: shipment.allowed_min_temp,
    allowedMax: shipment.allowed_max_temp,
  }));

  // Format positions for Leaflet Polyline
  const gpsTrail: [number, number][] = telemetry
    .filter((t) => t.latitude != null && t.longitude != null)
    .map((t) => [t.latitude, t.longitude]);

  const startPos = gpsTrail.length > 0 ? gpsTrail[0] : [20.5937, 78.9629] as [number, number];
  const endPos = gpsTrail.length > 0 ? gpsTrail[gpsTrail.length - 1] : [20.5937, 78.9629] as [number, number];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.8)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 99999,
        padding: '1.5rem',
        overflowY: 'auto'
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '1100px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '2rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem',
          borderRadius: '20px'
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0 }}>
                Shipment Audit & History
              </h2>
              <span className={`badge ${shipment.status === 'IN_TRANSIT' ? 'badge-success' : 'badge-warning'}`}>
                {shipment.status}
              </span>
            </div>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', margin: '4px 0 0 0', fontFamily: 'var(--font-mono)' }}>
              ID: {shipment.id} | Org: {shipment.organization_id} | Tracker: {shipment.tracker_id || 'Unassigned'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={handleExportCsv}
              disabled={exporting}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.85rem' }}
            >
              <Download size={16} />
              {exporting ? 'Exporting...' : 'Export CSV'}
            </button>

            <button
              onClick={onClose}
              style={{
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                padding: '8px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Metadata Details Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: 'rgba(15,23,42,0.6)', padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Calendar size={13} /> Started At
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '2px' }}>
              {shipment.started_at ? new Date(shipment.started_at).toLocaleString() : 'N/A'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={13} /> Ended At
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '2px' }}>
              {shipment.ended_at ? new Date(shipment.ended_at).toLocaleString() : 'Active In-Transit'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Thermometer size={13} color="var(--primary-cyan)" /> Allowed Temp Range
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--primary-cyan)', marginTop: '2px' }}>
              {shipment.allowed_min_temp}°C to {shipment.allowed_max_temp}°C
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldAlert size={13} color="var(--accent-amber)" /> Grace Period
            </div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '2px' }}>
              {shipment.grace_period_readings} consecutive bad readings
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            Loading shipment historical telemetry data...
          </div>
        ) : error ? (
          <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.1)', color: 'var(--accent-rose)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: '12px' }}>
            {error}
          </div>
        ) : (
          <>
            {/* Recharts Time-Series Chart Section */}
            <div className="glass-panel" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Thermometer size={18} color="var(--primary-cyan)" /> Temperature & Humidity Telemetry History
                </h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Total Readings: {telemetry.length}
                </span>
              </div>

              {chartData.length === 0 ? (
                <p style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  No telemetry records accumulated for this shipment yet.
                </p>
              ) : (
                <div style={{ width: '100%', height: '320px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="timestamp" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
                      <YAxis stroke="var(--text-muted)" tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', color: '#fff' }}
                        labelFormatter={(_, payload) => payload?.[0]?.payload?.fullTime || ''}
                      />
                      <Legend verticalAlign="top" height={36} />

                      {/* Threshold lines */}
                      <ReferenceLine y={shipment.allowed_max_temp} label={{ value: `Max (${shipment.allowed_max_temp}°C)`, fill: '#f43f5e', fontSize: 10 }} stroke="#f43f5e" strokeDasharray="4 4" />
                      <ReferenceLine y={shipment.allowed_min_temp} label={{ value: `Min (${shipment.allowed_min_temp}°C)`, fill: '#38bdf8', fontSize: 10 }} stroke="#38bdf8" strokeDasharray="4 4" />

                      <Line type="monotone" dataKey="temperature" name="Temperature (°C)" stroke="#38bdf8" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} />
                      <Line type="monotone" dataKey="humidity" name="Humidity (%)" stroke="#818cf8" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Leaflet GPS Route Trail Section */}
            <div className="glass-panel" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <MapPin size={18} color="var(--accent-emerald)" /> GPS Route Trail
                </h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {gpsTrail.length} Waypoints Recorded
                </span>
              </div>

              {gpsTrail.length === 0 ? (
                <p style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  No GPS waypoints recorded for this shipment.
                </p>
              ) : (
                <div style={{ height: '340px', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                  <MapContainer center={startPos} zoom={8} style={{ height: '100%', width: '100%', background: '#0b0f19' }}>
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />


                    {/* Connected Polyline Route */}
                    <Polyline positions={gpsTrail} color="#38bdf8" weight={4} opacity={0.85} />

                    {/* Route Start Position */}
                    <Marker position={startPos} icon={createPointIcon('#10b981')}>
                      <Popup>
                        <div style={{ color: '#0f172a', fontSize: '0.825rem' }}>
                          <strong>Route Start</strong><br />
                          Lat: {startPos[0]}, Lng: {startPos[1]}
                        </div>
                      </Popup>
                    </Marker>

                    {/* Route End / Latest Position */}
                    {gpsTrail.length > 1 && (
                      <Marker position={endPos} icon={createPointIcon('#f43f5e')}>
                        <Popup>
                          <div style={{ color: '#0f172a', fontSize: '0.825rem' }}>
                            <strong>Route Latest Position</strong><br />
                            Lat: {endPos[0]}, Lng: {endPos[1]}
                          </div>
                        </Popup>
                      </Marker>
                    )}
                  </MapContainer>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ShipmentHistoryModal;
