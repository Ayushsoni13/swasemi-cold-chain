import type { User, Tracker, Shipment, TelemetryReading, Alert, Organization } from '../types';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function getHeaders(token?: string | null): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const authToken = token || localStorage.getItem('swasemi_token');
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

export async function loginApi(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed. Please check your credentials.');
  }
  return res.json();
}

export async function getMeApi(token: string): Promise<User> {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: getHeaders(token),
  });
  if (!res.ok) {
    throw new Error('Failed to fetch user profile');
  }
  return res.json();
}

export async function fetchOrganizationsApi(): Promise<Organization[]> {
  const res = await fetch(`${API_BASE_URL}/organizations`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch organizations');
  }
  return res.json();
}

export async function createOrganizationApi(data: { id: string; name: string }): Promise<Organization> {
  const res = await fetch(`${API_BASE_URL}/organizations`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create organization');
  }
  return res.json();
}

export async function deleteOrganizationApi(orgId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/organizations/${encodeURIComponent(orgId)}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete organization');
  }
}

export async function fetchUsersApi(): Promise<User[]> {
  const res = await fetch(`${API_BASE_URL}/users`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch users');
  }
  return res.json();
}

export async function createUserApi(data: {
  email: string;
  password: string;
  role: string;
  organization_id?: string | null;
}): Promise<User> {
  const res = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create user');
  }
  return res.json();
}

export async function deleteUserApi(userId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete user');
  }
}

export async function createTrackerApi(data: {
  name: string;
  mqtt_topic: string;
  organization_id?: string;
}): Promise<Tracker> {
  const res = await fetch(`${API_BASE_URL}/trackers`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create tracker');
  }
  return res.json();
}

export async function deleteTrackerApi(trackerId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/trackers/${encodeURIComponent(trackerId)}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete tracker');
  }
}

export async function fetchTrackersApi(organizationId?: string): Promise<Tracker[]> {
  let url = `${API_BASE_URL}/trackers`;
  if (organizationId) {
    url += `?organization_id=${encodeURIComponent(organizationId)}`;
  }
  const res = await fetch(url, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error('Failed to fetch trackers');
  }
  return res.json();
}

export async function fetchShipmentsApi(organizationId?: string): Promise<Shipment[]> {
  let url = `${API_BASE_URL}/shipments`;
  if (organizationId) {
    url += `?organization_id=${encodeURIComponent(organizationId)}`;
  }
  const res = await fetch(url, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error('Failed to fetch shipments');
  }
  return res.json();
}

export async function startShipmentApi(data: {
  tracker_id: string;
  allowed_min_temp?: number;
  allowed_max_temp?: number;
  grace_period_readings?: number;
  organization_id?: string;
  origin_lat?: number;
  origin_lng?: number;
  target_lat?: number;
  target_lng?: number;
  route_name?: string;
}): Promise<Shipment> {
  const res = await fetch(`${API_BASE_URL}/shipments/start`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start shipment');
  }
  return res.json();
}

export async function endShipmentApi(shipmentId: string): Promise<Shipment> {
  const res = await fetch(`${API_BASE_URL}/shipments/${shipmentId}/end`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to end shipment');
  }
  return res.json();
}

export async function fetchShipmentTelemetryApi(shipmentId: string): Promise<TelemetryReading[]> {
  const res = await fetch(`${API_BASE_URL}/shipments/${shipmentId}/telemetry`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error('Failed to fetch shipment telemetry history');
  }
  return res.json();
}

export async function fetchAlertsApi(shipmentId?: string, trackerId?: string, organizationId?: string): Promise<Alert[]> {
  let url = `${API_BASE_URL}/alerts`;
  const params: string[] = [];
  if (shipmentId) params.push(`shipment_id=${encodeURIComponent(shipmentId)}`);
  if (trackerId) params.push(`tracker_id=${encodeURIComponent(trackerId)}`);
  if (organizationId) params.push(`organization_id=${encodeURIComponent(organizationId)}`);
  if (params.length > 0) url += `?${params.join('&')}`;

  const res = await fetch(url, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error('Failed to fetch alerts');
  }
  return res.json();
}

export async function exportShipmentCsvApi(shipmentId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/shipments/${shipmentId}/export`, {
    headers: getHeaders(),
  });
  if (!res.ok) {
    throw new Error('Failed to export shipment CSV');
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `shipment_${shipmentId}_telemetry.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
