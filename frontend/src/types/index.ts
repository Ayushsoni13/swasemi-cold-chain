export type Role = 'SUPER_ADMIN' | 'USER';

export interface User {
  id: string;
  organization_id: string | null;
  email: string;
  role: Role;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export interface Tracker {
  id: string;
  organization_id: string;
  name: string;
  mqtt_topic: string;
  status: 'ONLINE' | 'DELAYED' | 'OFFLINE' | string;
  last_seen: string | null;
  created_at: string;
}

export interface Shipment {
  id: string;
  organization_id: string;
  tracker_id: string | null;
  status: 'CREATED' | 'IN_TRANSIT' | 'DELIVERED' | 'CANCELLED' | string;
  started_at: string | null;
  ended_at: string | null;
  allowed_min_temp: number;
  allowed_max_temp: number;
  grace_period_readings: number;
  consecutive_breach_count?: number;
  breach_active: boolean;
  origin_lat?: number | null;
  origin_lng?: number | null;
  target_lat?: number | null;
  target_lng?: number | null;
  route_name?: string | null;
  created_at: string;
}

export interface TelemetryReading {
  id: string;
  organization_id: string;
  shipment_id: string | null;
  tracker_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number | null;
  battery_level: number | null;
  door_open: boolean;
}

export interface Alert {
  id: string;
  organization_id: string;
  shipment_id: string | null;
  tracker_id: string;
  alert_type: string;
  message: string;
  created_at: string;
  email_sent_at: string | null;
}

export interface WSTelemetryEvent {
  tracker_id: string;
  shipment_id: string;
  organization_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number | null;
  battery_level: number | null;
  door_open: boolean;
  status: 'ONLINE' | 'DELAYED' | 'OFFLINE' | string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
}
