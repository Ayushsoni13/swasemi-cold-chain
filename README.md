# SWASEMI® Cold-Chain Monitoring Platform

**SWASEMI®** is an enterprise multi-tenant cold-chain monitoring platform built with **Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Redis Pub/Sub, MQTT (`broker.emqx.io`), WebSockets, and React + TypeScript + Vite**.

---

## 1. Project Overview

The **SWASEMI® Cold-Chain Monitoring Platform** provides end-to-end real-time tracking, live moving GPS map visualization, and alert management for temperature-sensitive shipments across multiple pharmaceutical and logistics organizations.

### Key Features
- **Invite-Only Onboarding & Multi-Tenant Architecture**: Strict organization isolation. Only Super Admin can provision new tenant organizations, user accounts, and trucks. Public self-signup is disabled.
- **Super Admin Management Controls**: Super Admin can create and delete Organizations, Users, and Trackers/Trucks directly with confirmation modals and backend enforcement.
- **Live Moving GPS Map Tracking**: Leaflet interactive map with moving truck markers, polyline route trails, and direction headings. Supports preset routes such as **Ahmedabad $\rightarrow$ Gandhinagar** (Gujarat Express), Bengaluru $\rightarrow$ Chennai, Mumbai $\rightarrow$ Pune, Delhi $\rightarrow$ Jaipur, Hyderabad $\rightarrow$ Vijayawada, and custom coordinates.
- **Real-Time Telemetry Ingestion via MQTT**: Ingests temperature, humidity, battery, door status, and GPS coordinates using `broker.emqx.io`.
- **Active Shipment Telemetry Gate**: Telemetry received before shipment start or after shipment end is explicitly ignored and NOT stored as shipment history.
- **Low-Latency Real-Time Push**: Redis Pub/Sub and WebSocket fan-out without frontend polling. WebSocket connections are strictly organization-scoped.
- **Temperature Breach & Grace-Period Engine**: Supports allowed min/max thresholds, consecutive-reading grace periods, and continuous breach state handling.
- **SMTP Email Alert Delivery**: Real SMTP email delivery with a single-email constraint per continuous breach (resets upon recovery).
- **Shipment Audit & Visual Analytics**: Recharts time-series graphs with min/max threshold reference lines and Leaflet historical GPS route trails.
- **Tenant-Scoped CSV Data Export**: Downloads audit-ready CSV telemetry reports for any shipment.
- **Corporate SWASEMI® Branding**: Tailored design system with corporate branding (`SWA` in deep blue `#0284c7`, `SEMi` in vibrant orange `#f97316`, and `®` emblem).

---

## 2. Architecture

```text
       [Telemetry Simulator / Moving Trackers (Ahmedabad → Gandhinagar, etc.)]
                                      │
                                      ▼ MQTT (swasemi/coldchain/trackers/{tracker_id})
                              [EMQX MQTT Broker]
                                      │
                                      ▼ Background Subscriber (paho-mqtt)
                              [FastAPI Ingestion Engine]
                              ├── 1. Validate Pydantic Schema
                              ├── 2. Verify Active Shipment Gate (IN_TRANSIT)
                              ├── 3. Evaluate Temperature Breach & Grace Period
                              ├── 4. Store Telemetry & Alert Records in Database
                              └── 5. Publish to Redis Pub/Sub Channel
                                      │
                                      ├──────────────────────────┐
                                      ▼                          ▼
                             [Redis Pub/Sub Channel]     [SMTP Email Service]
                                      │                     (Real SMTP / TLS)
                                      ▼
                            [WebSocket Server (/ws)]
                                      │
                                      ▼ Real-Time Push (No Polling)
                         [React + TypeScript + Leaflet Dashboard]
```

---

## 3. Mandatory Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL / SQLite, Alembic, Redis Pub/Sub, PyJWT, `paho-mqtt`, `passlib` / `bcrypt`, `pytest`
- **Frontend**: React 19, TypeScript, Vite, React-Leaflet, Leaflet, Recharts, Lucide React, Vanilla CSS
- **Simulator**: Standalone Python MQTT Telemetry Generator with moving tracker route math
- **MQTT Broker**: EMQX Public Broker (`broker.emqx.io:1883`)
- **Infrastructure**: Docker & Docker Compose (PostgreSQL, Redis, Backend, Frontend, Simulator)

---

## 4. Multi-Tenancy & Security Rules

1. Every tracker belongs to exactly one organization.
2. Every shipment belongs to exactly one organization.
3. Every telemetry record belongs to exactly one organization.
4. Normal users can access only their assigned organization.
5. Super Admin can access all organizations.
6. There is **NO public signup**. Accounts are provisioned exclusively by Super Admin.
7. JWT authentication is required (`Authorization: Bearer <TOKEN>`).
8. Normal user `organization_id` comes strictly from JWT claims (never trusted from user request bodies).
9. Cross-tenant access attempts return `404 Not Found` to prevent resource discovery.

---

## 5. Telemetry & Alert Engine Rules

1. **Shipment Telemetry Gate**: `Start Shipment` explicitly activates telemetry storage for that shipment. Telemetry before shipment start or after shipment end is NOT stored.
2. **Grace Period**: Bad readings increment `consecutive_breach_count`. Alerts trigger only when `consecutive_breach_count >= grace_period_readings`.
3. **Single Email Constraint**: One continuous temperature breach generates **only one email**.
4. **Recovery & Re-breach**: Returning to allowed bounds clears breach state. A new breach after recovery triggers a new email.

---

## 6. Seed / Demo Accounts

| Role | Email | Password | Organization ID | Organization Name |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@swasemi.demo` | `DemoAdmin123!` | System-wide (`None`) | All Organizations Access |
| **User A** | `usera@swasemi.demo` | `DemoUser123!` | `org-pharma-a` | PharmaCorp Global |
| **User B** | `userb@swasemi.demo` | `DemoUser123!` | `org-biocold-b` | BioCold Logistics |

---

## 7. API Endpoints Reference

### Health Check
- `GET /health` - Service health status

### Authentication
- `POST /auth/login` - Authenticate & obtain JWT access token
- `GET /auth/me` - Get current authenticated user profile

### Super Admin Operations (Super Admin Only)
- `GET /organizations` - List all organizations
- `POST /organizations` - Create new organization
- `DELETE /organizations/{org_id}` - Delete organization
- `GET /users` - List all users
- `POST /users` - Provision user account
- `DELETE /users/{user_id}` - Delete user account

### Trackers & Trucks
- `GET /trackers` - List trackers (tenant-scoped or org filtered)
- `GET /trackers/{tracker_id}` - Get tracker details
- `POST /trackers` - Create new tracker
- `DELETE /trackers/{tracker_id}` - Delete tracker

### Shipments
- `GET /shipments` - List shipments
- `POST /shipments/start` - Start shipment (activates telemetry gate, sets origin/target GPS route)
- `POST /shipments/{shipment_id}/end` - End shipment (deactivates telemetry gate)
- `GET /shipments/{shipment_id}/telemetry` - Historical time-series telemetry
- `GET /shipments/{shipment_id}/export` - Download CSV audit report

### Alerts
- `GET /alerts` - List temperature breach alerts

---

## 8. Local Setup & Execution

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
python app/db/seed.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Telemetry Simulator
```bash
python simulator/simulator.py
```

### 4. Running Pytest Test Suite
```bash
cd backend
.\venv\Scripts\pytest.exe
```
All **55 unit & integration tests** should pass cleanly.

---

## 9. Docker Compose Deployment

To build and run the entire stack with containerized PostgreSQL, Redis, Backend, Frontend, and Simulator:

```bash
docker-compose up --build
```

Services started:
- **PostgreSQL**: `5432`
- **Redis**: `6379`
- **Backend API**: `8000`
- **Frontend Dashboard**: `5173`
- **Telemetry Simulator**: Background Service

---

## 10. Production Deployment Instructions

- **Frontend**: Build production bundle via `npm run build` (`dist/`). Deploy to Vercel, Netlify, or AWS S3 + CloudFront. Set `VITE_BACKEND_URL=https://api.yourdomain.com`.
- **Backend**: Deploy Docker container to Render, Railway, or AWS ECS.
- **Database**: Managed PostgreSQL (AWS RDS / Render Postgres / Neon).
- **Redis**: Managed Redis (Upstash / AWS ElastiCache / Render Redis).
