# SWASEMI® Cold-Chain Monitoring Platform
## Technical Assessment & Project Submission Document

**Submitted by**: Ayush Soni  
**Company**: SWASEMI  

---

### 1. Project Overview
The **SWASEMI Cold-Chain Monitoring Platform** is a multi-tenant web application designed to monitor refrigerated shipments using simulated IoT telemetry. The system provides live tracker locations, temperature and humidity monitoring, shipment lifecycle control, historical shipment analysis, temperature alerts, organization-level access control, and CSV export.

The implementation uses **React + TypeScript + Vite, FastAPI, PostgreSQL, Redis Pub/Sub, MQTT, WebSockets, JWT authentication, Leaflet, Recharts**, and cloud deployment.

---

### 2. Project and Submission Information

| Item | Details |
| :--- | :--- |
| **Company** | SWASEMI |
| **Project** | Cold-Chain Monitoring Platform |
| **Candidate** | Ayush Soni |
| **Repository** | [https://github.com/Ayushsoni13/swasemi-cold-chain](https://github.com/Ayushsoni13/swasemi-cold-chain) |
| **Frontend Deployment** | [https://swasemi-cold-chain.vercel.app](https://swasemi-cold-chain.vercel.app) |
| **Backend API** | [https://swasemi-backend.onrender.com](https://swasemi-backend.onrender.com) |
| **Swagger API Documentation** | [https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs) |
| **Frontend Technology** | React 19 + TypeScript + Vite |
| **Backend Technology** | Python 3.11+ + FastAPI + Pydantic v2 |
| **Database** | PostgreSQL |
| **Real-Time Messaging** | Redis Pub/Sub |
| **Telemetry Protocol** | MQTT (`broker.emqx.io`) |
| **Map** | Leaflet / React-Leaflet |
| **Charts** | Recharts |
| **Authentication** | JWT Bearer authentication |

---

### 3. How to Review the Project
- Open the live frontend: [https://swasemi-cold-chain.vercel.app](https://swasemi-cold-chain.vercel.app)
- Use one of the demo accounts listed in Section 4.
- Review the dashboard, organization-scoped data, live tracker locations, shipment controls, telemetry and alerts.
- Open Swagger API documentation: [https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs)
- Review the source code and project structure in GitHub: [https://github.com/Ayushsoni13/swasemi-cold-chain](https://github.com/Ayushsoni13/swasemi-cold-chain)
- Open the backend root/API deployment: [https://swasemi-backend.onrender.com](https://swasemi-backend.onrender.com)

---

### 4. Demo Accounts
*Public self-signup is disabled by design. Account provisioning is restricted to Super Admins.*

| Account Role | Email | Password | Scope & Privileges |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@swasemi.demo` | `DemoAdmin123!` | System-wide access; manages organizations, users, trackers and shipments |
| **User A (Tenant 1)** | `usera@swasemi.demo` | `DemoUser123!` | Tenant-isolated access: `org-pharma-a` / PharmaCorp |
| **User B (Tenant 2)** | `userb@swasemi.demo` | `DemoUser123!` | Tenant-isolated access: `org-biocold-b` / BioCold |

---

### 5. System Architecture
- **React + TypeScript + Vite** frontend
- **REST API** and **WebSocket** communication
- **FastAPI** backend
- **JWT authentication** and organization-based authorization
- **PostgreSQL** for organizations, users, trackers, shipments and telemetry history
- **MQTT broker (`broker.emqx.io`)** for telemetry ingestion
- **Redis Pub/Sub** for real-time organization-scoped fan-out
- **WebSocket** delivery to connected frontend clients
- **Background simulator** for moving trackers and telemetry
- **SMTP email delivery** for temperature breach alerts

---

### 6. Representative Project Structure

```text
swasemi-cold-chain/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── ...
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── main.py
│   ├── alembic/
│   └── requirements.txt
│
├── tests/
├── docker-compose.yml
├── AGENTS.md
├── PROJECT_SUBMISSION_DOCUMENT.md
└── README.md
```

---

### 7. Core Functional Features

- **Multi-Tenant Architecture**: Complete tenant data isolation across PostgreSQL models, queries, WebSockets, and JWT tokens. Normal users can access only data belonging to their organization; Super Admin can access all organizations.
- **Active Shipment Telemetry Gate**: Telemetry storage is strictly active only while a shipment is `IN_TRANSIT`. Readings before shipment start or after shipment completion are ignored.
- **Real-Time Telemetry & Zero Polling**: Telemetry is ingested through MQTT using `broker.emqx.io`, distributed through Redis Pub/Sub, and streamed to the frontend over WebSockets without frontend polling.
- **Temperature Breach & Grace Period Engine**: Temperature readings are evaluated against configured minimum and maximum limits and consecutive bad readings. A single SMTP email alert is sent for one continuous breach and the alert state resets after recovery.
- **Interactive Map & Audit Visuals**: The platform provides real-time moving Leaflet map markers, historical route polylines, Recharts time-series temperature charts, and CSV data export.
- **Autonomous Cloud Deployment**: The production backend includes a background simulator service running with the FastAPI deployment on Render, providing live telemetry and map movement without requiring evaluator-side local simulator execution.
- **Automated Testing**: The project includes 55 unit and integration tests, reported as passing cleanly in the final project validation.

---

### 8. Shipment Lifecycle and Telemetry Rules
- A tracker is associated with an organization and can have an active shipment.
- `Start Shipment` changes the shipment into the active/in-transit state.
- Telemetry is accepted and persisted only while the shipment is active.
- Telemetry received before shipment start is not stored.
- Telemetry received after shipment completion is not stored.
- `End Shipment` closes the active shipment and stops telemetry persistence for that shipment.
- The simulator publishes moving tracker telemetry through MQTT.

---

### 9. Multi-Tenancy and Security
- Each normal user belongs to one organization.
- Trackers, shipments and telemetry records are organization-scoped.
- Organization context for authenticated users is derived from the JWT/session context rather than trusted from arbitrary user request data.
- Backend authorization enforces tenant isolation, including API and WebSocket access.
- Super Admin operates at system level and can manage multiple organizations.
- Public self-registration is disabled.
- JWT Bearer authentication is required for protected API access.

---

### 10. Real-Time Telemetry Flow
1. The simulator publishes telemetry to the MQTT broker.
2. FastAPI receives and validates telemetry payloads.
3. The shipment gate determines whether the reading may be persisted.
4. Accepted readings are stored in PostgreSQL.
5. Telemetry events are published to the organization-scoped Redis Pub/Sub channel.
6. WebSocket connections receive only the events authorized for their organization.
7. The React dashboard updates the live map and telemetry display without frontend polling.

---

### 11. Temperature Monitoring and Alerts
- Shipment temperature limits can be configured using minimum and maximum thresholds.
- The alert engine detects consecutive out-of-range readings according to the configured grace period.
- A continuous breach generates one email alert rather than repeated emails for every bad reading.
- When temperature returns to the valid range, the breach state recovers.
- A later, separate breach after recovery generates a new alert.
- SMTP is used for real email delivery.

---

### 12. Historical Monitoring
- Historical shipment temperature data can be displayed as time-series charts using Recharts.
- Historical GPS readings can be visualized as a route/trail on the map.
- Telemetry/history data can be exported as CSV for audit and review.

---

### 13. API and Integration Review

| Resource / Interface | Purpose |
| :--- | :--- |
| **REST API** | Authentication, organizations, users, trackers, shipments, history and export operations |
| **Swagger / OpenAPI** | [https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs) |
| **WebSocket** | Live organization-scoped telemetry updates |
| **MQTT** | Telemetry ingestion from simulator/tracker source |
| **Redis Pub/Sub** | Real-time event fan-out |
| **PostgreSQL** | Persistent application and telemetry data |
| **SMTP** | Temperature breach email notifications |

---

### 14. Deployment

| Component | Deployment |
| :--- | :--- |
| **Frontend** | Vercel |
| **Backend** | Render |
| **Database** | Render PostgreSQL |
| **Redis** | Render Redis |
| **MQTT Broker** | `broker.emqx.io` |
| **Source Control** | GitHub |

*The deployed application is intended to be reviewable without requiring the evaluator to run the project locally.*

---

### 15. Assessment Compliance Matrix

| # | Assessment Requirement | Status |
| :--- | :--- | :--- |
| **1** | Multi-tenant architecture | **PASSED** |
| **2** | Every tracker belongs to exactly 1 org | **PASSED** |
| **3** | Every shipment belongs to exactly 1 org | **PASSED** |
| **4** | Every telemetry record belongs to 1 org | **PASSED** |
| **5** | Normal users access only their org | **PASSED** |
| **6** | Super Admin accesses all orgs | **PASSED** |
| **7** | NO public signup | **PASSED** |
| **8** | Only Super Admin creates orgs/users | **PASSED** |
| **9** | JWT authentication required | **PASSED** |
| **10** | Backend enforces tenant isolation | **PASSED** |
| **11** | Never trust `organization_id` from user body | **PASSED** |
| **12** | Org ID comes strictly from JWT | **PASSED** |
| **13** | Start shipment activates telemetry storage | **PASSED** |
| **14** | Telemetry before start NOT stored | **PASSED** |
| **15** | Telemetry after end NOT stored | **PASSED** |
| **16** | MQTT used for telemetry ingestion | **PASSED** |
| **17** | Moving trackers in simulator | **PASSED** |
| **18** | Redis used for real-time fan-out | **PASSED** |
| **19** | WebSocket provides live updates | **PASSED** |
| **20** | Zero frontend polling for live telemetry | **PASSED** |
| **21** | WebSockets organization scoped | **PASSED** |
| **22** | Temperature min/max limits supported | **PASSED** |
| **23** | Consecutive grace period supported | **PASSED** |
| **24** | 1 continuous breach = 1 email alert | **PASSED** |
| **25** | New breach after recovery = new email | **PASSED** |
| **26** | Real SMTP email delivery supported | **PASSED** |
| **27** | Historical shipment temperature chart | **PASSED** |
| **28** | Historical GPS route trail | **PASSED** |
| **29** | CSV data export required | **PASSED** |
| **30** | Autonomous deployment without local code | **PASSED** |

---

### 16. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite |
| **Backend** | Python 3.11+, FastAPI, Pydantic v2 |
| **Authentication** | JWT Bearer |
| **Database** | PostgreSQL |
| **ORM / Persistence** | SQLAlchemy 2.x / Alembic |
| **Real-Time** | Redis Pub/Sub + WebSocket |
| **IoT Telemetry** | MQTT (`broker.emqx.io`) |
| **Simulator** | Python-based moving tracker simulator service |
| **Mapping** | Leaflet / React-Leaflet |
| **Charts** | Recharts |
| **Email** | SMTP |
| **Testing** | pytest (55 unit & integration tests) |
| **Containerization** | Docker / Docker Compose |
| **Deployment** | Vercel + Render |
| **Version Control** | Git + GitHub |

---

### 17. Testing and Validation
The final project validation reported **55 unit and integration tests passing cleanly**. The validation also covered frontend build, database migration, MQTT telemetry flow, Redis/WebSocket real-time behavior, SMTP alert delivery, security/tenant isolation, and end-to-end application behavior.

---

### 18. Evaluation Checklist
- Open the live frontend: [https://swasemi-cold-chain.vercel.app](https://swasemi-cold-chain.vercel.app)
- Log in as Super Admin (`admin@swasemi.demo`) and review system-wide access.
- Log in as User A (`usera@swasemi.demo`) and verify organization-specific data (`org-pharma-a`).
- Log in as User B (`userb@swasemi.demo`) and verify that User A's tenant data is not accessible.
- Review Start Shipment and End Shipment behavior.
- Observe live tracker movement and telemetry.
- Review temperature charts, GPS trail and CSV export.
- Review temperature alert behavior where applicable.
- Open Swagger ([https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs)) and inspect the available API endpoints.
- Review the GitHub repository ([https://github.com/Ayushsoni13/swasemi-cold-chain](https://github.com/Ayushsoni13/swasemi-cold-chain)) for source code, configuration, tests and documentation.

---

### 19. Important Review URLs

| Purpose | URL |
| :--- | :--- |
| **Live Frontend** | [https://swasemi-cold-chain.vercel.app](https://swasemi-cold-chain.vercel.app) |
| **Backend API** | [https://swasemi-backend.onrender.com](https://swasemi-backend.onrender.com) |
| **Swagger / OpenAPI** | [https://swasemi-backend.onrender.com/docs](https://swasemi-backend.onrender.com/docs) |
| **GitHub Repository** | [https://github.com/Ayushsoni13/swasemi-cold-chain](https://github.com/Ayushsoni13/swasemi-cold-chain) |

---

### 20. Submission Notes
This document is provided as the technical assessment and project submission summary for **SWASEMI**. The live links above provide direct access to the deployed application, backend API, and API documentation, while the GitHub repository provides access to the source code and project materials.

**Candidate**: Ayush Soni  
**Company**: SWASEMI  
