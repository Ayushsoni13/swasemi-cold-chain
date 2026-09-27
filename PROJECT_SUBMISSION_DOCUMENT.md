# SWASEMI® Cold-Chain Monitoring Platform
## Technical Assessment & Project Submission Document

---

### Executive Summary

The **SWASEMI® Cold-Chain Monitoring Platform** is an enterprise-grade, multi-tenant real-time cold-chain tracking and telemetry platform designed for pharmaceutical logistics and temperature-sensitive shipment monitoring.

It delivers real-time moving GPS map tracking, temperature and humidity telemetry ingestion via MQTT, automated alert breach detection with grace period rules, single-email SMTP notification delivery, live WebSocket updates without frontend polling, historical time-series analytics, and audit CSV exports.

---

### Live Application & Repository Links

| System Component | Live URL / Location | Description |
| :--- | :--- | :--- |
| **Live Frontend App** | [https://swasemi-cold-chain.vercel.app](https://swasemi-cold-chain.vercel.app) | Production SPA built with React 19, TypeScript, Vite & Leaflet |
| **Live Backend API** | [https://swasemi-backend.onrender.com](https://swasemi-backend.onrender.com) | FastAPI REST API & WebSocket Server on Render |
| **Swagger API Docs** | [https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs) | Interactive OpenAPI documentation & live endpoint testing |
| **GitHub Repository** | [https://github.com/Ayushsoni13/swasemi-cold-chain](https://github.com/Ayushsoni13/swasemi-cold-chain) | Complete source code, backend, frontend & Docker configs |

---

### Demo Account Credentials

| Account Role | Email Login | Password | Organization Scope | Access Rights |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@swasemi.demo` | `DemoAdmin123!` | System-wide (`None`) | Can manage all orgs, users, trackers, shipments & alerts |
| **Organization User A** | `usera@swasemi.demo` | `DemoUser123!` | `org-pharma-a` (PharmaCorp) | Tenant isolated: view & manage PharmaCorp shipments |
| **Organization User B** | `userb@swasemi.demo` | `DemoUser123!` | `org-biocold-b` (BioCold) | Tenant isolated: view & manage BioCold shipments |

*Note: Public self-signup is disabled by design. Account creation is strictly restricted to Super Admins.*

---

### Architecture & Telemetry Data Flow

```text
  [Background Simulator / Moving Tracker (Ahmedabad → Gandhinagar)]
                                 │
                                 ▼ MQTT (swasemi/coldchain/trackers/{tracker_id})
                         [EMQX Broker (broker.emqx.io)]
                                 │
                                 ▼ Background MQTT Ingestion
                         [FastAPI Ingestion Engine]
                         ├── 1. Validate Pydantic Telemetry Payload
                         ├── 2. Active Shipment Telemetry Gate Check
                         ├── 3. Breach & Grace Period Engine Evaluation
                         ├── 4. PostgreSQL Database Persistence
                         └── 5. Redis Pub/Sub Event Broadcast
                                 │
                                 ├──────────────────────────┐
                                 ▼                          ▼
                        [Redis Pub/Sub Channel]     [SMTP Email Service]
                                 │                   (Breach Alert Dispatch)
                                 ▼
                       [WebSocket Server (/ws)]
                                 │
                                 ▼ Real-Time Push (Zero Frontend Polling)
                    [React 19 + TypeScript + Leaflet Dashboard]
```

---

### Core Technical Features & Architecture Highlights

#### 1. Multi-Tenant Architecture & Security
- **Strict Isolation**: Trackers, shipments, telemetry, and alerts are tied to an `organization_id`.
- **JWT Authentication**: Normal users are bound to their organization ID derived from JWT claims. Normal users cannot view or manipulate data belonging to other organizations.
- **Super Admin Privilege**: Super Admin accounts possess system-wide visibility and management controls (create/delete organizations, provision user accounts, create/delete trackers).

#### 2. Active Shipment Telemetry Gate
- Telemetry storage is explicitly gated by shipment status.
- Telemetry received **before shipment start** or **after shipment end** is ignored and not recorded into shipment history.

#### 3. Real-Time Telemetry & Zero Polling Architecture
- Live telemetry is ingested over MQTT (`broker.emqx.io`).
- Telemetry data fan-outs instantly via **Redis Pub/Sub** and **WebSockets** directly to the frontend.
- No frontend interval polling (`setInterval` / REST polling) is used for live updates.

#### 4. Temperature Breach & Grace Period Engine
- Configurable `allowed_min_temp` and `allowed_max_temp` thresholds per shipment.
- Configurable `grace_period_readings` (consecutive bad readings threshold).
- **Single Email Rule**: A continuous temperature breach triggers **only one email notification**. When temperature recovers and breaches again later, a new email notification is dispatched.

#### 5. Interactive GPS Map & Visual Analytics
- Leaflet map featuring real-time moving markers, directional bearing markers, and GPS polyline route trails (e.g., Ahmedabad to Gandhinagar express route).
- Historical Recharts time-series charts with min/max reference lines.
- One-click tenant-scoped CSV data export for shipment audit compliance.

---

### Mandatory Assessment Requirements Compliance Matrix

| # | Assessment Requirement | Status | Implementation Detail |
| :--- | :--- | :--- | :--- |
| **1** | Multi-tenant architecture | **PASSED** | Data models enforced with `organization_id` |
| **2** | Every tracker belongs to 1 org | **PASSED** | Foreign key constraint on `trackers.organization_id` |
| **3** | Every shipment belongs to 1 org | **PASSED** | Foreign key constraint on `shipments.organization_id` |
| **4** | Every telemetry record belongs to 1 org | **PASSED** | Enforced via `telemetry.organization_id` |
| **5** | Normal users access only their org | **PASSED** | Middleware & service query filtering using JWT tenant context |
| **6** | Super Admin accesses all orgs | **PASSED** | Super Admin bypasses org filter |
| **7** | NO public signup | **PASSED** | Self-registration endpoint removed |
| **8** | Only Super Admin creates orgs/users | **PASSED** | Protected endpoints `POST /organizations` & `POST /users` |
| **9** | JWT authentication required | **PASSED** | Bearer token authentication on all protected routes |
| **10** | Backend enforces tenant isolation | **PASSED** | Verified in backend database query filters |
| **11** | Never trust `organization_id` from user | **PASSED** | Payload `organization_id` ignored for normal users |
| **12** | Org ID comes from JWT | **PASSED** | Derived from `current_user.organization_id` |
| **13** | Start shipment activates telemetry | **PASSED** | `status` set to `IN_TRANSIT` |
| **14** | Telemetry before start NOT stored | **PASSED** | Active shipment gate validates `IN_TRANSIT` state |
| **15** | Telemetry after end NOT stored | **PASSED** | `COMPLETED` / `CANCELLED` shipments ignore telemetry |
| **16** | MQTT used for telemetry | **PASSED** | Ingested via `paho-mqtt` on `broker.emqx.io` |
| **17** | At least 3 moving trackers in simulator | **PASSED** | TRK-001, TRK-002, TRK-003 moving routes configured |
| **18** | Redis for real-time fan-out | **PASSED** | Redis Pub/Sub channel `coldchain:telemetry` |
| **19** | WebSocket provides live updates | **PASSED** | WebSocket endpoint `/ws` |
| **20** | No polling for live telemetry | **PASSED** | Native WebSocket pushes |
| **21** | WebSockets organization scoped | **PASSED** | WS connection validates JWT and filters events |
| **22** | Min/max limits supported | **PASSED** | Evaluated on every telemetry reading |
| **23** | Consecutive grace period supported | **PASSED** | Tracked via `consecutive_breach_count` |
| **24** | 1 continuous breach = 1 email | **PASSED** | Controlled via `is_active_breach` state |
| **25** | New breach after recovery = new email | **PASSED** | State resets upon temperature recovery |
| **26** | Real SMTP delivery supported | **PASSED** | Configured via `app.services.email_service` |
| **27** | Historical shipment temperature chart | **PASSED** | Interactive Recharts component |
| **28** | Historical GPS trail | **PASSED** | Leaflet GPS route trail polyline |
| **29** | CSV export required | **PASSED** | `GET /shipments/{id}/export` downloads audit CSV |
| **30** | Deployment works autonomously | **PASSED** | Background simulator service runs automatically on Render |

---

### Verification & Automated Testing

- **Backend Test Suite**: Written using `pytest` and `httpx`.
- **Test Results**: All **55 unit and integration tests** pass cleanly without errors or warnings.
- **Coverage**:
  - `test_auth.py` (10 tests)
  - `test_health.py` (2 tests)
  - `test_phase3.py` (12 tests - Multi-tenancy & CRUD)
  - `test_phase4.py` (10 tests - Telemetry Gate & Ingestion)
  - `test_phase5.py` (10 tests - Alerts, Grace Period & Single Email)
  - `test_phase6.py` (11 tests - WebSockets, CSV Export & Background Services)

---

### Mandatory Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Alembic, Redis Pub/Sub, PyJWT, `paho-mqtt`, `pytest`
- **Frontend**: React 19, TypeScript, Vite, React-Leaflet, Leaflet, Recharts, Lucide React, Vanilla CSS
- **Infrastructure**: Docker & Docker Compose, Render (Backend API + Postgres + Redis), Vercel (Frontend SPA)
