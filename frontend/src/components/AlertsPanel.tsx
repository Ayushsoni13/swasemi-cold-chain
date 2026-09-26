import React from 'react';
import { AlertTriangle, Mail, Clock, ShieldAlert } from 'lucide-react';
import type { Alert } from '../types';

interface AlertsPanelProps {
  alerts: Alert[];
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({ alerts }) => {
  if (alerts.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <AlertTriangle size={32} color="var(--accent-emerald)" style={{ marginBottom: '8px' }} />
        <p style={{ margin: 0, fontSize: '0.9rem' }}>No temperature breach alerts recorded. Cold chain operates within allowed thresholds.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldAlert size={20} color="var(--accent-rose)" />
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Temperature & System Alerts</h2>
        </div>
        <span className="badge badge-error">{alerts.length} Active Alert Records</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {alerts.map((alert) => (
          <div
            key={alert.id}
            style={{
              background: 'rgba(244, 63, 94, 0.08)',
              border: '1px solid rgba(244, 63, 94, 0.25)',
              borderRadius: '12px',
              padding: '1rem 1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="badge badge-error" style={{ fontSize: '0.7rem' }}>
                  {alert.alert_type}
                </span>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Tracker: {alert.tracker_id}
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Clock size={12} />
                {new Date(alert.created_at).toLocaleString()}
              </div>
            </div>

            <p style={{ fontSize: '0.875rem', color: '#f8fafc', margin: '4px 0 0 0', lineHeight: '1.5' }}>
              {alert.message}
            </p>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px', marginTop: '4px' }}>
              <div>
                <strong>Shipment:</strong> <span style={{ fontFamily: 'var(--font-mono)' }}>{alert.shipment_id || 'N/A'}</span> | <strong>Org:</strong> {alert.organization_id}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: alert.email_sent_at ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                <Mail size={12} />
                {alert.email_sent_at ? 'SMTP Email Delivered' : 'Email Pending'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AlertsPanel;
