# SWASEMI Cold-Chain Monitoring Platform - Project Rules

## Project Goal

Build the SWASEMI Cold-Chain Monitoring Platform according to the provided assessment.

This is a 36-hour maximum coding assessment. Prioritize working P0 functionality, security, multi-tenancy, real-time telemetry and deployment over UI polish or unnecessary features.

## Mandatory Stack

Backend:
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- JWT
- Redis
- MQTT using broker.emqx.io

Frontend:
- React
- TypeScript
- Vite
- React-Leaflet / Leaflet
- Recharts

Testing:
- pytest

Infrastructure:
- Docker
- Docker Compose

## Critical Requirements

1. Multi-tenant architecture.
2. Every tracker belongs to exactly one organization.
3. Every shipment belongs to exactly one organization.
4. Every telemetry record belongs to exactly one organization.
5. Normal users can access only their organization.
6. Super Admin can access all organizations.
7. There is NO public signup.
8. Only Super Admin can create organizations and users.
9. JWT authentication is required.
10. Backend must enforce organization isolation.
11. Never trust organization_id supplied by normal users.
12. Organization ID for normal users must come from JWT.
13. Start Shipment must explicitly activate telemetry storage.
14. Telemetry before shipment start must NOT be stored as shipment history.
15. Telemetry after shipment end must NOT be stored for that shipment.
16. MQTT must be used for simulator telemetry.
17. At least 3 moving trackers must exist in the simulator.
18. Redis must be used for real-time fan-out.
19. WebSocket must provide live updates.
20. Do not use polling for live telemetry.
21. WebSocket connections must be organization scoped.
22. Temperature min/max limits must be supported.
23. Consecutive-reading grace period must be supported.
24. One continuous temperature breach must generate only one email.
25. A new breach after recovery may generate another email.
26. Real SMTP email delivery must be supported.
27. Historical shipment temperature chart is required.
28. Historical GPS trail is required.
29. CSV export is required.
30. Production deployment must work without evaluator running local code.

## Architecture

Simulator
    ↓
MQTT broker
    ↓
FastAPI MQTT ingestion
    ↓
Validate payload
    ↓
Check active shipment
    ↓
PostgreSQL
    ↓
Redis Pub/Sub
    ↓
WebSocket
    ↓
React dashboard

## Do NOT Add

Do not introduce:
- Kafka
- Kubernetes
- Celery
- microservices
- unnecessary message queues
- unnecessary abstractions
- unnecessary dependencies

Keep the implementation simple.

## Code Quality

- Use Python type hints.
- Use TypeScript types.
- Use Pydantic schemas.
- Keep services modular but simple.
- Do not create unnecessary repository abstractions.
- Do not leave dead code.
- Do not leave TODO placeholders for required features.
- Do not fake MQTT, Redis, WebSockets or email.

## Security

Never expose:
- passwords
- JWT secrets
- database passwords
- SMTP passwords
- MQTT credentials

Use environment variables.

Do not commit .env.

Use .env.example.

## Development Rule

Work in phases.

Before moving to the next major phase:
1. Run tests.
2. Run the application.
3. Verify the relevant feature.
4. Fix errors.
5. Give a concise summary.

Do not rewrite working code unnecessarily.

## Token Efficiency

Do not repeatedly explain the whole project.

Read AGENTS.md and existing code before making changes.

Only modify files necessary for the current task.

Do not regenerate files that already work.

## Priority

P0 correctness
>
security and tenant isolation
>
shipment telemetry gate
>
MQTT
>
Redis
>
WebSocket
>
alerts/email
>
deployment
>
P1 history/CSV
>
UI polish