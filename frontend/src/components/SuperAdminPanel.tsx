import React, { useState, useEffect } from 'react';
import { Building2, Users, Truck, Plus, Shield, CheckCircle2, AlertCircle, RefreshCw, X, Trash2 } from 'lucide-react';
import type { Organization, User, Tracker } from '../types';
import {
  fetchOrganizationsApi,
  createOrganizationApi,
  deleteOrganizationApi,
  fetchUsersApi,
  createUserApi,
  deleteUserApi,
  createTrackerApi,
  deleteTrackerApi,
  fetchTrackersApi
} from '../services/api';

interface SuperAdminPanelProps {
  onClose: () => void;
  onDataChanged: () => void;
}

export const SuperAdminPanel: React.FC<SuperAdminPanelProps> = ({ onClose, onDataChanged }) => {
  const [activeTab, setActiveTab] = useState<'orgs' | 'users' | 'trackers'>('orgs');

  // Data states
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [trackers, setTrackers] = useState<Tracker[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form states - Organization
  const [newOrgId, setNewOrgId] = useState<string>('');
  const [newOrgName, setNewOrgName] = useState<string>('');

  // Form states - User
  const [newUserEmail, setNewUserEmail] = useState<string>('');
  const [newUserPassword, setNewUserPassword] = useState<string>('');
  const [newUserRole, setNewUserRole] = useState<'USER' | 'SUPER_ADMIN'>('USER');
  const [newUserOrgId, setNewUserOrgId] = useState<string>('');

  // Form states - Tracker
  const [newTrackerName, setNewTrackerName] = useState<string>('');
  const [newTrackerTopic, setNewTrackerTopic] = useState<string>('');
  const [newTrackerOrgId, setNewTrackerOrgId] = useState<string>('');

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [orgsData, usersData, trackersData] = await Promise.all([
        fetchOrganizationsApi(),
        fetchUsersApi(),
        fetchTrackersApi(),
      ]);
      setOrganizations(orgsData);
      setUsers(usersData);
      setTrackers(trackersData);

      if (orgsData.length > 0 && !newUserOrgId) {
        setNewUserOrgId(orgsData[0].id);
      }
      if (orgsData.length > 0 && !newTrackerOrgId) {
        setNewTrackerOrgId(orgsData[0].id);
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to load admin management data' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  // Handle Create Organization
  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgId.trim() || !newOrgName.trim()) return;

    setActionLoading(true);
    setStatusMessage(null);
    try {
      await createOrganizationApi({ id: newOrgId.trim(), name: newOrgName.trim() });
      setStatusMessage({ type: 'success', text: `Organization '${newOrgName}' created successfully!` });
      setNewOrgId('');
      setNewOrgName('');
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to create organization' });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Provision User
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserEmail.trim() || !newUserPassword.trim()) return;
    if (newUserRole === 'USER' && !newUserOrgId) {
      setStatusMessage({ type: 'error', text: 'Organization is required for Normal Users' });
      return;
    }

    setActionLoading(true);
    setStatusMessage(null);
    try {
      await createUserApi({
        email: newUserEmail.trim(),
        password: newUserPassword,
        role: newUserRole,
        organization_id: newUserRole === 'USER' ? newUserOrgId : null,
      });
      setStatusMessage({ type: 'success', text: `User account '${newUserEmail}' provisioned successfully!` });
      setNewUserEmail('');
      setNewUserPassword('');
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to provision user' });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Create Tracker / Shipment Truck
  const handleCreateTracker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTrackerName.trim() || !newTrackerTopic.trim() || !newTrackerOrgId) return;

    setActionLoading(true);
    setStatusMessage(null);
    try {
      await createTrackerApi({
        name: newTrackerName.trim(),
        mqtt_topic: newTrackerTopic.trim(),
        organization_id: newTrackerOrgId,
      });
      setStatusMessage({ type: 'success', text: `Shipment Truck / Tracker '${newTrackerName}' created successfully!` });
      setNewTrackerName('');
      setNewTrackerTopic('');
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to create tracker' });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Delete Organization
  const handleDeleteOrg = async (orgId: string, orgName: string) => {
    if (!confirm(`Are you sure you want to delete organization '${orgName}' (${orgId})? This will also remove associated trackers, shipments, and users.`)) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await deleteOrganizationApi(orgId);
      setStatusMessage({ type: 'success', text: `Organization '${orgName}' deleted successfully!` });
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete organization' });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Delete User Account
  const handleDeleteUser = async (userId: string, email: string) => {
    if (!confirm(`Are you sure you want to delete user account '${email}'?`)) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await deleteUserApi(userId);
      setStatusMessage({ type: 'success', text: `User account '${email}' deleted successfully!` });
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete user' });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Delete Tracker / Shipment Truck
  const handleDeleteTracker = async (trackerId: string, trackerName: string) => {
    if (!confirm(`Are you sure you want to delete shipment truck / tracker '${trackerName}' (${trackerId})?`)) return;
    setActionLoading(true);
    setStatusMessage(null);
    try {
      await deleteTrackerApi(trackerId);
      setStatusMessage({ type: 'success', text: `Shipment Truck / Tracker '${trackerName}' deleted successfully!` });
      await loadAdminData();
      onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete tracker' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(5, 8, 16, 0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1.5rem' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '900px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        
        {/* Header */}
        <div style={{ padding: '1.25rem 1.75rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(15, 23, 42, 0.6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: 'var(--accent-emerald)', padding: '8px', borderRadius: '10px' }}>
              <Shield size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                Super Admin Onboarding & Management Center
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                Provision organizations, manage invite-only user accounts & registered shipment trucks
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '4px' }}>
            <X size={22} />
          </button>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div style={{
            padding: '10px 1.5rem',
            background: statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
            borderBottom: `1px solid ${statusMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
            color: statusMessage.type === 'success' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {statusMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            {statusMessage.text}
          </div>
        )}

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', background: 'rgba(11, 15, 25, 0.5)' }}>
          <button
            onClick={() => { setActiveTab('orgs'); setStatusMessage(null); }}
            style={{
              flex: 1,
              padding: '14px',
              background: activeTab === 'orgs' ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'orgs' ? '2px solid var(--primary-cyan)' : '2px solid transparent',
              color: activeTab === 'orgs' ? 'var(--primary-cyan)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <Building2 size={18} />
            Organizations ({organizations.length})
          </button>

          <button
            onClick={() => { setActiveTab('users'); setStatusMessage(null); }}
            style={{
              flex: 1,
              padding: '14px',
              background: activeTab === 'users' ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'users' ? '2px solid var(--primary-cyan)' : '2px solid transparent',
              color: activeTab === 'users' ? 'var(--primary-cyan)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <Users size={18} />
            Provision Users ({users.length})
          </button>

          <button
            onClick={() => { setActiveTab('trackers'); setStatusMessage(null); }}
            style={{
              flex: 1,
              padding: '14px',
              background: activeTab === 'trackers' ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'trackers' ? '2px solid var(--primary-cyan)' : '2px solid transparent',
              color: activeTab === 'trackers' ? 'var(--primary-cyan)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <Truck size={18} />
            Shipment Trucks / Trackers ({trackers.length})
          </button>
        </div>

        {/* Tab Contents */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin" style={{ marginBottom: '0.5rem' }} />
              <p>Loading records...</p>
            </div>
          ) : (
            <>
              {/* TAB 1: ORGANIZATIONS */}
              {activeTab === 'orgs' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <form onSubmit={handleCreateOrg} style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1rem', alignItems: 'end' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Organization ID (Unique Key)
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. org-swasemi-01"
                        value={newOrgId}
                        onChange={(e) => setNewOrgId(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Organization Name
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Swasemi Logistics North"
                        value={newOrgName}
                        onChange={(e) => setNewOrgName(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <button type="submit" className="btn-primary" disabled={actionLoading} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                      <Plus size={16} />
                      {actionLoading ? 'Creating...' : 'Create Organization'}
                    </button>
                  </form>

                  {/* Table */}
                  <div>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                      Registered Organizations
                    </h3>
                    <div style={{ background: 'rgba(15, 23, 42, 0.3)', borderRadius: '10px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                        <thead>
                          <tr style={{ background: 'rgba(15, 23, 42, 0.7)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-dim)' }}>
                            <th style={{ padding: '10px 16px' }}>Organization ID</th>
                            <th style={{ padding: '10px 16px' }}>Name</th>
                            <th style={{ padding: '10px 16px' }}>Created Date</th>
                            <th style={{ padding: '10px 16px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {organizations.map((org) => (
                            <tr key={org.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                              <td style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--primary-cyan)' }}>{org.id}</td>
                              <td style={{ padding: '10px 16px', color: '#ffffff' }}>{org.name}</td>
                              <td style={{ padding: '10px 16px', color: 'var(--text-dim)' }}>{new Date(org.created_at).toLocaleString()}</td>
                              <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                <button
                                  onClick={() => handleDeleteOrg(org.id, org.name)}
                                  title="Delete Organization"
                                  style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--accent-rose)', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer' }}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: PROVISION USERS */}
              {activeTab === 'users' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <form onSubmit={handleCreateUser} style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr 120px 1fr auto', gap: '1rem', alignItems: 'end' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        User Email
                      </label>
                      <input
                        type="email"
                        required
                        placeholder="newuser@org.com"
                        value={newUserEmail}
                        onChange={(e) => setNewUserEmail(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Password
                      </label>
                      <input
                        type="password"
                        required
                        placeholder="••••••••"
                        value={newUserPassword}
                        onChange={(e) => setNewUserPassword(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Role
                      </label>
                      <select
                        value={newUserRole}
                        onChange={(e) => setNewUserRole(e.target.value as 'USER' | 'SUPER_ADMIN')}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      >
                        <option value="USER">Normal User</option>
                        <option value="SUPER_ADMIN">Super Admin</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Assigned Organization
                      </label>
                      <select
                        disabled={newUserRole === 'SUPER_ADMIN'}
                        value={newUserOrgId}
                        onChange={(e) => setNewUserOrgId(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem', opacity: newUserRole === 'SUPER_ADMIN' ? 0.5 : 1 }}
                      >
                        {organizations.map((org) => (
                          <option key={org.id} value={org.id}>
                            {org.name} ({org.id})
                          </option>
                        ))}
                      </select>
                    </div>

                    <button type="submit" className="btn-primary" disabled={actionLoading} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                      <Plus size={16} />
                      {actionLoading ? 'Provisioning...' : 'Add Account'}
                    </button>
                  </form>

                  {/* Users Table */}
                  <div>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                      Provisioned User Accounts
                    </h3>
                    <div style={{ background: 'rgba(15, 23, 42, 0.3)', borderRadius: '10px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                        <thead>
                          <tr style={{ background: 'rgba(15, 23, 42, 0.7)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-dim)' }}>
                            <th style={{ padding: '10px 16px' }}>Email</th>
                            <th style={{ padding: '10px 16px' }}>Role</th>
                            <th style={{ padding: '10px 16px' }}>Organization</th>
                            <th style={{ padding: '10px 16px' }}>Created Date</th>
                            <th style={{ padding: '10px 16px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {users.map((u) => (
                            <tr key={u.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                              <td style={{ padding: '10px 16px', fontWeight: 600, color: '#ffffff' }}>{u.email}</td>
                              <td style={{ padding: '10px 16px' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  fontSize: '0.7rem',
                                  fontWeight: 700,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  background: u.role === 'SUPER_ADMIN' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                                  color: u.role === 'SUPER_ADMIN' ? 'var(--accent-emerald)' : 'var(--primary-cyan)'
                                }}>
                                  {u.role === 'SUPER_ADMIN' && <Shield size={12} />}
                                  {u.role}
                                </span>
                              </td>
                              <td style={{ padding: '10px 16px', color: u.organization_id ? 'var(--primary-cyan)' : 'var(--text-dim)' }}>
                                {u.organization_id || 'Global (None)'}
                              </td>
                              <td style={{ padding: '10px 16px', color: 'var(--text-dim)' }}>{new Date(u.created_at).toLocaleString()}</td>
                              <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                <button
                                  onClick={() => handleDeleteUser(u.id, u.email)}
                                  title="Delete User"
                                  style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--accent-rose)', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer' }}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: SHIPMENT TRUCKS / TRACKERS */}
              {activeTab === 'trackers' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <form onSubmit={handleCreateTracker} style={{ background: 'rgba(15, 23, 42, 0.5)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '1rem', alignItems: 'end' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Truck / Tracker Name
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Truck 04 - Cold Bay"
                        value={newTrackerName}
                        onChange={(e) => setNewTrackerName(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        MQTT Topic
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="swasemi/telemetry/tracker-04"
                        value={newTrackerTopic}
                        onChange={(e) => setNewTrackerTopic(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                        Target Organization
                      </label>
                      <select
                        value={newTrackerOrgId}
                        onChange={(e) => setNewTrackerOrgId(e.target.value)}
                        style={{ width: '100%', background: 'rgba(5, 8, 16, 0.8)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '8px 12px', color: '#ffffff', fontSize: '0.85rem' }}
                      >
                        {organizations.map((org) => (
                          <option key={org.id} value={org.id}>
                            {org.name} ({org.id})
                          </option>
                        ))}
                      </select>
                    </div>

                    <button type="submit" className="btn-primary" disabled={actionLoading} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
                      <Plus size={16} />
                      {actionLoading ? 'Creating...' : 'Add Truck Tracker'}
                    </button>
                  </form>

                  {/* Trackers Table */}
                  <div>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
                      Registered Trackers & Shipment Trucks
                    </h3>
                    <div style={{ background: 'rgba(15, 23, 42, 0.3)', borderRadius: '10px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                        <thead>
                          <tr style={{ background: 'rgba(15, 23, 42, 0.7)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-dim)' }}>
                            <th style={{ padding: '10px 16px' }}>Tracker ID</th>
                            <th style={{ padding: '10px 16px' }}>Name</th>
                            <th style={{ padding: '10px 16px' }}>MQTT Topic</th>
                            <th style={{ padding: '10px 16px' }}>Organization</th>
                            <th style={{ padding: '10px 16px' }}>Status</th>
                            <th style={{ padding: '10px 16px', textAlign: 'right' }}>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trackers.map((tr) => (
                            <tr key={tr.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                              <td style={{ padding: '10px 16px', fontWeight: 600, color: 'var(--primary-cyan)' }}>{tr.id}</td>
                              <td style={{ padding: '10px 16px', color: '#ffffff' }}>{tr.name}</td>
                              <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: 'var(--text-dim)' }}>{tr.mqtt_topic}</td>
                              <td style={{ padding: '10px 16px', color: 'var(--primary-cyan)' }}>{tr.organization_id}</td>
                              <td style={{ padding: '10px 16px' }}>
                                <span style={{
                                  fontSize: '0.7rem',
                                  fontWeight: 700,
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  background: tr.status === 'ONLINE' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                                  color: tr.status === 'ONLINE' ? 'var(--accent-emerald)' : 'var(--text-dim)'
                                }}>
                                  {tr.status}
                                </span>
                              </td>
                              <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                                <button
                                  onClick={() => handleDeleteTracker(tr.id, tr.name)}
                                  title="Delete Tracker"
                                  style={{ background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', color: 'var(--accent-rose)', padding: '6px 10px', borderRadius: '6px', cursor: 'pointer' }}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default SuperAdminPanel;
