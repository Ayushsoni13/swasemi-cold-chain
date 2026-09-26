import React, { useState, useEffect, useCallback } from 'react';
import { Truck, Shield, LogOut, Radio, Battery, Thermometer, Droplets, DoorOpen, MapPin, Play, Square, RefreshCw, History, FileText, Download, Building2 } from 'lucide-react';
import type { User, Tracker, Shipment, WSTelemetryEvent, Alert, Organization } from '../types';
import { fetchTrackersApi, fetchShipmentsApi, startShipmentApi, endShipmentApi, fetchAlertsApi, exportShipmentCsvApi, fetchShipmentTelemetryApi, fetchOrganizationsApi } from '../services/api';

import { useWebSocket } from '../hooks/useWebSocket';
import { TrackerMap } from './TrackerMap';
import { AlertsPanel } from './AlertsPanel';
import { ShipmentHistoryModal } from './ShipmentHistoryModal';
import { SuperAdminPanel } from './SuperAdminPanel';

import { SwasemiLogo } from './SwasemiLogo';

interface DashboardProps {
  user: User;
  token: string;
  onLogout: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ user, token, onLogout }) => {
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [allTrackers, setAllTrackers] = useState<Tracker[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [latestTelemetry, setLatestTelemetry] = useState<Record<string, WSTelemetryEvent>>({});

  // Modal States
  const [showStartModal, setShowStartModal] = useState<boolean>(false);
  const [showSuperAdminPanel, setShowSuperAdminPanel] = useState<boolean>(false);
  const [selectedShipmentForHistory, setSelectedShipmentForHistory] = useState<Shipment | null>(null);

  // Form State for Start Shipment
  const [selectedTrackerId, setSelectedTrackerId] = useState<string>('');
  const [minTemp, setMinTemp] = useState<number>(2.0);
  const [maxTemp, setMaxTemp] = useState<number>(8.0);
  const [graceReadings, setGraceReadings] = useState<number>(3);
  const [selectedPresetRoute, setSelectedPresetRoute] = useState<string>('ahmedabad-gandhinagar');
  const [customOriginLat, setCustomOriginLat] = useState<number>(23.0225);
  const [customOriginLng, setCustomOriginLng] = useState<number>(72.5714);
  const [customTargetLat, setCustomTargetLat] = useState<number>(23.2156);
  const [customTargetLng, setCustomTargetLng] = useState<number>(72.6369);
  const [customRouteName, setCustomRouteName] = useState<string>('Ahmedabad -> Gandhinagar');
  const [startModalOrgId, setStartModalOrgId] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Load Initial API Data
  const loadData = useCallback(async () => {
    try {
      const orgFilter = selectedOrgId || undefined;
      const [trackersRes, allTrackersRes, shipmentsRes, alertsRes, orgsRes] = await Promise.allSettled([
        fetchTrackersApi(orgFilter),
        fetchTrackersApi(undefined),
        fetchShipmentsApi(orgFilter),
        fetchAlertsApi(undefined, undefined, orgFilter),
        user.role === 'SUPER_ADMIN' ? fetchOrganizationsApi() : Promise.resolve([]),
      ]);

      if (trackersRes.status === 'fulfilled') setTrackers(trackersRes.value);
      if (allTrackersRes.status === 'fulfilled') setAllTrackers(allTrackersRes.value);
      if (shipmentsRes.status === 'fulfilled') setShipments(shipmentsRes.value);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value);
      if (orgsRes.status === 'fulfilled') setOrganizations(orgsRes.value);

      const shipmentsData = shipmentsRes.status === 'fulfilled' ? shipmentsRes.value : [];



      // Pre-populate latest telemetry from database for active shipments
      const activeShipments = shipmentsData.filter((s) => s.status === 'IN_TRANSIT');
      if (activeShipments.length > 0) {
        const telemetryPromises = activeShipments.map(async (shipment) => {
          try {
            const readings = await fetchShipmentTelemetryApi(shipment.id);
            if (readings && readings.length > 0) {
              const lastReading = readings[readings.length - 1];
              return {
                tracker_id: shipment.tracker_id,
                event: {
                  tracker_id: shipment.tracker_id,
                  shipment_id: shipment.id,
                  organization_id: shipment.organization_id,
                  timestamp: lastReading.timestamp,
                  latitude: lastReading.latitude,
                  longitude: lastReading.longitude,
                  temperature: lastReading.temperature,
                  humidity: lastReading.humidity,
                  battery_level: lastReading.battery_level,
                  door_open: lastReading.door_open,
                  status: 'ONLINE',
                } as WSTelemetryEvent,
              };
            }
          } catch (e) {
            return null;
          }
          return null;
        });

        const results = await Promise.all(telemetryPromises);
        const initialTelemetry: Record<string, WSTelemetryEvent> = {};
        results.forEach((item) => {
          if (item && item.tracker_id) {
            initialTelemetry[item.tracker_id] = item.event;
          }
        });

        setLatestTelemetry((prev) => ({
          ...initialTelemetry,
          ...prev,
        }));
      }
    } catch (err: any) {
      console.error(err.message || 'Failed to load dashboard data');
    }
  }, [selectedOrgId, user.role]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // WebSocket Message Handler
  const handleWSMessage = useCallback((event: WSTelemetryEvent) => {
    setLatestTelemetry((prev) => ({
      ...prev,
      [event.tracker_id]: event,
    }));

    // Update tracker status locally in list
    setTrackers((prevTrackers) =>
      prevTrackers.map((t) =>
        t.id === event.tracker_id
          ? { ...t, status: event.status, last_seen: event.timestamp }
          : t
      )
    );

    // Periodically fetch alerts when telemetry updates
    fetchAlertsApi().then(setAlerts).catch(() => {});
  }, []);

  // Connect WebSocket with Reconnect Backoff
  const { connectionState } = useWebSocket(token, handleWSMessage);

  // Calculate Dashboard Metrics
  const totalTrackers = trackers.length;
  const onlineTrackers = trackers.filter((t) => {
    const status = latestTelemetry[t.id]?.status || t.status;
    return status === 'ONLINE';
  }).length;
  const offlineTrackers = totalTrackers - onlineTrackers;
  const activeShipmentsCount = shipments.filter((s) => s.status === 'IN_TRANSIT').length;

  // Handle Start Shipment
  const handleStartShipmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTrackerId) return;
    setActionLoading(true);
    try {
      const targetTracker = trackers.find((t) => t.id === selectedTrackerId);

      let oLat = customOriginLat;
      let oLng = customOriginLng;
      let tLat = customTargetLat;
      let tLng = customTargetLng;
      let rName = customRouteName;

      if (selectedPresetRoute === 'ahmedabad-gandhinagar') {
        oLat = 23.0225; oLng = 72.5714; tLat = 23.2156; tLng = 72.6369; rName = 'Ahmedabad -> Gandhinagar';
      } else if (selectedPresetRoute === 'bengaluru-chennai') {
        oLat = 12.9716; oLng = 77.5946; tLat = 13.0827; tLng = 80.2707; rName = 'Bengaluru -> Chennai';
      } else if (selectedPresetRoute === 'mumbai-pune') {
        oLat = 19.0760; oLng = 72.8777; tLat = 18.5204; tLng = 73.8567; rName = 'Mumbai -> Pune';
      } else if (selectedPresetRoute === 'delhi-jaipur') {
        oLat = 28.7041; oLng = 77.1025; tLat = 26.9124; tLng = 75.7873; rName = 'Delhi -> Jaipur';
      } else if (selectedPresetRoute === 'hyderabad-vijayawada') {
        oLat = 17.3850; oLng = 78.4867; tLat = 16.5062; tLng = 80.6480; rName = 'Hyderabad -> Vijayawada';
      }

      await startShipmentApi({
        tracker_id: selectedTrackerId,
        organization_id: targetTracker?.organization_id,
        allowed_min_temp: Number(minTemp),
        allowed_max_temp: Number(maxTemp),
        grace_period_readings: Number(graceReadings),
        origin_lat: oLat,
        origin_lng: oLng,
        target_lat: tLat,
        target_lng: tLng,
        route_name: rName,
      });

      setShowStartModal(false);
      setSelectedTrackerId('');
      await loadData(); // Refresh shipments list
    } catch (err: any) {
      alert(err.message || 'Failed to start shipment');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle End Shipment
  const handleEndShipment = async (shipmentId: string) => {
    if (!confirm('Are you sure you want to end this active shipment?')) return;
    setActionLoading(true);
    try {
      await endShipmentApi(shipmentId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to end shipment');
    } finally {
      setActionLoading(false);
    }
  };

  // Export CSV Helper
  const handleExportCsv = async (shipmentId: string) => {
    try {
      await exportShipmentCsvApi(shipmentId);
    } catch (err: any) {
      alert(err.message || 'Export failed');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '1rem 2rem' }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <SwasemiLogo height={32} showTagline={true} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            {/* WS Connection Status Badge */}
            <div
              className={`badge ${
                connectionState === 'CONNECTED'
                  ? 'badge-success'
                  : connectionState === 'RECONNECTING'
                  ? 'badge-warning'
                  : 'badge-error'
              }`}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Radio size={14} className={connectionState === 'CONNECTED' ? 'pulse' : ''} />
              WebSocket: {connectionState}
            </div>

            {/* Organization Scope Dropdown (Super Admin only) */}
            {user.role === 'SUPER_ADMIN' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Building2 size={16} color="var(--primary-cyan)" />
                <select
                  id="admin-org-filter"
                  value={selectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    border: '1px solid var(--border-color)',
                    color: '#ffffff',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <option value="">All Organizations (Global View)</option>
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name} ({org.id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Super Admin Management Button */}
            {user.role === 'SUPER_ADMIN' && (
              <button
                id="super-admin-manage-btn"
                onClick={() => setShowSuperAdminPanel(true)}
                style={{
                  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.2))',
                  color: 'var(--accent-emerald)',
                  border: '1px solid rgba(16, 185, 129, 0.4)',
                  padding: '7px 14px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  boxShadow: '0 4px 12px rgba(16, 185, 129, 0.15)',
                }}
              >
                <Shield size={16} />
                Admin Panel (Onboarding)
              </button>
            )}

            {/* User Info Badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', background: 'rgba(255,255,255,0.05)', padding: '6px 14px', borderRadius: '999px', border: '1px solid var(--border-color)' }}>
              {user.role === 'SUPER_ADMIN' ? <Shield size={16} color="var(--accent-emerald)" /> : <Truck size={16} color="var(--primary-cyan)" />}
              <span>{user.email}</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', borderLeft: '1px solid var(--border-color)', paddingLeft: '8px' }}>
                {user.role === 'SUPER_ADMIN' ? 'SUPER ADMIN' : user.organization_id}
              </span>
            </div>

            <button id="logout-btn" onClick={onLogout} style={{ background: 'rgba(244,63,94,0.1)', color: 'var(--accent-rose)', border: '1px solid rgba(244,63,94,0.25)', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1280px', width: '100%', margin: '2rem auto', padding: '0 1.5rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
        
        {/* Super Admin Quick Actions Banner */}
        {user.role === 'SUPER_ADMIN' && (
          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(2, 132, 199, 0.08))', border: '1px solid rgba(16, 185, 129, 0.25)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Shield size={24} color="var(--accent-emerald)" />
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#ffffff' }}>
                  Super Admin Management Portal
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Invite-only onboarding: Provision new tenant organizations, user accounts, and shipment trucks.
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => setShowSuperAdminPanel(true)}
                className="btn-primary"
                style={{ padding: '8px 14px', fontSize: '0.85rem' }}
              >
                <Building2 size={16} />
                Create Organization / User / Truck
              </button>
            </div>
          </div>
        )}
        
        {/* Metric Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>Total Trackers</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)' }}>{totalTrackers}</div>
          </div>

          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>Online Trackers</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>{onlineTrackers}</div>
          </div>

          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>Offline / Delayed</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-amber)' }}>{offlineTrackers}</div>
          </div>

          <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '6px' }}>Active Shipments</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--primary-cyan)' }}>{activeShipmentsCount}</div>
          </div>
        </div>

        {/* Temperature Breach & System Alerts Section */}
        <AlertsPanel alerts={alerts} />

        {/* Live Map Section */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MapPin size={20} color="var(--primary-cyan)" />
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Live Tracker Locations</h2>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Real-time updates via WebSocket Pub/Sub</span>
          </div>
          <TrackerMap trackers={trackers} shipments={shipments} latestTelemetry={latestTelemetry} />

        </div>

        {/* Action Header & Tracker Grid */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Monitored Trackers & Live Telemetry</h2>
            
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => loadData()} style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-main)', border: '1px solid var(--border-color)', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                <RefreshCw size={14} /> Refresh
              </button>

              <button
                id="start-shipment-modal-btn"
                onClick={async () => {
                  await loadData();
                  setShowStartModal(true);
                }}
                className="btn-primary"
              >
                <Play size={16} /> Start Shipment
              </button>

            </div>
          </div>

          {/* Tracker Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.25rem' }}>
            {trackers.map((t) => {
              const tel = latestTelemetry[t.id];
              const status = tel ? tel.status : t.status;
              const activeShipment = shipments.find((s) => s.tracker_id === t.id && s.status === 'IN_TRANSIT');

              return (
                <div key={t.id} className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>{t.name}</h3>
                        <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{t.id}</span>
                      </div>

                      <span className={`badge ${status === 'ONLINE' ? 'badge-success' : status === 'DELAYED' ? 'badge-warning' : 'badge-error'}`}>
                        {status}
                      </span>
                    </div>

                    {/* Telemetry Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Thermometer size={14} color="var(--primary-cyan)" /> Temp
                        </div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: tel && (tel.temperature < (activeShipment?.allowed_min_temp ?? 2) || tel.temperature > (activeShipment?.allowed_max_temp ?? 8)) ? 'var(--accent-rose)' : 'var(--text-main)' }}>
                          {tel ? `${tel.temperature}°C` : '4.2°C'}
                        </div>
                      </div>

                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Droplets size={14} color="#818cf8" /> Humidity
                        </div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                          {tel?.humidity ? `${tel.humidity}%` : '55.0%'}
                        </div>
                      </div>

                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Battery size={14} color="var(--accent-emerald)" /> Battery
                        </div>
                        <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                          {tel?.battery_level ? `${tel.battery_level}%` : '98%'}
                        </div>
                      </div>

                      <div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <DoorOpen size={14} color="var(--accent-amber)" /> Door
                        </div>
                        <div style={{ fontSize: '1rem', fontWeight: 600 }}>
                          {tel ? (tel.door_open ? 'OPEN' : 'CLOSED') : 'CLOSED'}
                        </div>
                      </div>
                    </div>

                  </div>

                  {/* Active Shipment Info & Control */}
                  <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                    {activeShipment ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', fontWeight: 700 }}>ACTIVE SHIPMENT</div>
                            <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{activeShipment.id.substring(0, 18)}...</div>
                          </div>

                          <div style={{ display: 'flex', gap: '6px' }}>
                            <button
                              onClick={() => setSelectedShipmentForHistory(activeShipment)}
                              style={{ background: 'rgba(56, 189, 248, 0.15)', color: 'var(--primary-cyan)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '6px 10px', borderRadius: '8px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                              <History size={13} /> Charts
                            </button>

                            <button
                              onClick={() => handleEndShipment(activeShipment.id)}
                              disabled={actionLoading}
                              style={{ background: 'rgba(244, 63, 94, 0.15)', color: 'var(--accent-rose)', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '6px 10px', borderRadius: '8px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}
                            >
                              <Square size={13} /> End
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                        No active shipment running
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Historical Shipment Audit Section */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <History size={20} color="var(--primary-cyan)" />
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Shipment History & Telemetry Audit</h2>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {shipments.length} Total Shipments Recorded
            </span>
          </div>

          {shipments.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9rem' }}>No shipment records found.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>Shipment ID</th>
                    <th style={{ padding: '10px' }}>Tracker</th>
                    <th style={{ padding: '10px' }}>Org</th>
                    <th style={{ padding: '10px' }}>Status</th>
                    <th style={{ padding: '10px' }}>Temp Range</th>
                    <th style={{ padding: '10px' }}>Grace Period</th>
                    <th style={{ padding: '10px' }}>Started At</th>
                    <th style={{ padding: '10px' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {shipments.map((s) => (
                    <tr key={s.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '12px 10px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{s.id.substring(0, 16)}...</td>
                      <td style={{ padding: '12px 10px' }}>{s.tracker_id || 'N/A'}</td>
                      <td style={{ padding: '12px 10px' }}>{s.organization_id}</td>
                      <td style={{ padding: '12px 10px' }}>
                        <span className={`badge ${s.status === 'IN_TRANSIT' ? 'badge-success' : 'badge-warning'}`}>
                          {s.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px 10px', color: 'var(--primary-cyan)', fontWeight: 600 }}>
                        {s.allowed_min_temp}°C - {s.allowed_max_temp}°C
                      </td>
                      <td style={{ padding: '12px 10px' }}>{s.grace_period_readings} readings</td>
                      <td style={{ padding: '12px 10px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                        {s.started_at ? new Date(s.started_at).toLocaleString() : 'N/A'}
                      </td>
                      <td style={{ padding: '12px 10px' }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            onClick={() => setSelectedShipmentForHistory(s)}
                            style={{ background: 'rgba(56, 189, 248, 0.1)', color: 'var(--primary-cyan)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                          >
                            <FileText size={12} /> View Charts
                          </button>
                          <button
                            onClick={() => handleExportCsv(s.id)}
                            style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                          >
                            <Download size={12} /> CSV
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Start Shipment Modal */}
        {showStartModal && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '1rem' }}>
            <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '2rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1.5rem' }}>Start New Cold-Chain Shipment</h3>

              <form onSubmit={handleStartShipmentSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                
                {/* Organization Selection (Super Admin only) */}
                {user.role === 'SUPER_ADMIN' && (
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Select Organization / Cold Storage
                    </label>
                    <select
                      value={startModalOrgId}
                      onChange={(e) => {
                        setStartModalOrgId(e.target.value);
                        setSelectedTrackerId('');
                      }}
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem', outline: 'none' }}
                    >
                      <option value="">-- All Organizations (Global View) --</option>
                      {organizations.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.name} ({org.id})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Select Tracker / Truck
                  </label>
                  <select
                    required
                    value={selectedTrackerId}
                    onChange={(e) => setSelectedTrackerId(e.target.value)}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem', outline: 'none' }}
                  >
                    <option value="">-- Choose Tracker / Truck --</option>
                    {(allTrackers.length > 0 ? allTrackers : trackers)
                      .filter((t) => !startModalOrgId || t.organization_id === startModalOrgId)
                      .map((t) => {
                        const activeShipment = shipments.find((s) => s.tracker_id === t.id && s.status === 'IN_TRANSIT');
                        const org = organizations.find((o) => o.id === t.organization_id);
                        const orgLabel = org ? `${org.name}` : t.organization_id;
                        return (
                          <option key={t.id} value={t.id} disabled={!!activeShipment}>
                            {t.name} ({t.id}) — Org: {orgLabel} {activeShipment ? '[ACTIVE IN-TRANSIT]' : ''}
                          </option>
                        );
                      })}
                  </select>
                  {(allTrackers.length > 0 ? allTrackers : trackers).filter((t) => !startModalOrgId || t.organization_id === startModalOrgId).length === 0 && (
                    <div style={{ marginTop: '8px', padding: '8px 12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', fontSize: '0.75rem', color: '#fca5a5' }}>
                      ⚠️ No trucks/trackers found for this organization. Please create a truck in the Admin Panel.
                    </div>
                  )}
                </div>



                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Select Route / Destination
                  </label>
                  <select
                    value={selectedPresetRoute}
                    onChange={(e) => setSelectedPresetRoute(e.target.value)}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem', outline: 'none' }}
                  >
                    <option value="ahmedabad-gandhinagar">📍 Ahmedabad → Gandhinagar (Gujarat Express)</option>
                    <option value="bengaluru-chennai">📍 Bengaluru → Chennai (South Corridor)</option>
                    <option value="mumbai-pune">📍 Mumbai → Pune (West Corridor)</option>
                    <option value="delhi-jaipur">📍 Delhi → Jaipur (North Corridor)</option>
                    <option value="hyderabad-vijayawada">📍 Hyderabad → Vijayawada (Deccan Route)</option>
                    <option value="custom">⚙️ Custom Coordinates (Manual Entry)</option>
                  </select>
                </div>

                {selectedPresetRoute === 'custom' && (
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Route Name</label>
                      <input type="text" value={customRouteName} onChange={(e) => setCustomRouteName(e.target.value)} style={{ width: '100%', background: '#050810', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '0.8rem' }} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Start Lat, Lng</label>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <input type="number" step="0.0001" value={customOriginLat} onChange={(e) => setCustomOriginLat(Number(e.target.value))} style={{ width: '50%', background: '#050810', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '0.8rem' }} />
                          <input type="number" step="0.0001" value={customOriginLng} onChange={(e) => setCustomOriginLng(Number(e.target.value))} style={{ width: '50%', background: '#050810', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '0.8rem' }} />
                        </div>
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Target Lat, Lng</label>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <input type="number" step="0.0001" value={customTargetLat} onChange={(e) => setCustomTargetLat(Number(e.target.value))} style={{ width: '50%', background: '#050810', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '0.8rem' }} />
                          <input type="number" step="0.0001" value={customTargetLng} onChange={(e) => setCustomTargetLng(Number(e.target.value))} style={{ width: '50%', background: '#050810', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '0.8rem' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Allowed Min Temp (°C)
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      required
                      value={minTemp}
                      onChange={(e) => setMinTemp(Number(e.target.value))}
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                      Allowed Max Temp (°C)
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      required
                      value={maxTemp}
                      onChange={(e) => setMaxTemp(Number(e.target.value))}
                      style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem' }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Grace Period Readings
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={graceReadings}
                    onChange={(e) => setGraceReadings(Number(e.target.value))}
                    style={{ width: '100%', background: '#0f172a', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '10px', color: '#ffffff', fontSize: '0.9rem' }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '1rem' }}>
                  <button type="button" onClick={() => setShowStartModal(false)} style={{ background: 'transparent', color: 'var(--text-muted)', border: '1px solid var(--border-color)', padding: '10px 18px', borderRadius: '8px', cursor: 'pointer' }}>
                    Cancel
                  </button>

                  <button type="submit" className="btn-primary" disabled={actionLoading}>
                    {actionLoading ? 'Starting...' : 'Confirm & Start Shipment'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Shipment History & Chart Modal */}
        {selectedShipmentForHistory && (
          <ShipmentHistoryModal
            shipment={selectedShipmentForHistory}
            onClose={() => setSelectedShipmentForHistory(null)}
          />
        )}

        {/* Super Admin Management Center Modal */}
        {showSuperAdminPanel && (
          <SuperAdminPanel
            onClose={() => setShowSuperAdminPanel(false)}
            onDataChanged={loadData}
          />
        )}

      </main>

      <footer style={{ padding: '1.5rem 0', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem', marginTop: 'auto' }}>
        SWASEMI Cold-Chain Monitoring Platform &copy; 2026
      </footer>
    </div>
  );
};

export default Dashboard;
