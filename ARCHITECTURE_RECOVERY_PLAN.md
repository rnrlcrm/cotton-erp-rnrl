# Architecture Recovery Plan

## Stage 0 – Stabilize Current Monolith (Week 0–1)
- [ ] Confirm canonical surface: freeze `backend/modules/**` routers/services as source of truth, mark `backend/api/v1/**` as deprecated and map parity gaps.
- [ ] Eliminate sync session stack:
  - [x] Stop using `SessionLocal` in `backend/app/main.py` readiness probe.
  - [ ] Replace remaining runtime imports of `backend.db.session_module` with async equivalents.
  - [ ] Remove `backend/db/session_module.py` after migrating scripts/tests.
- [ ] Regenerate clean Alembic history that matches current models; drop stale `backend/migrations` tree.
- [ ] Run baseline smoke tests (migrations, uvicorn, critical API flows) and document results.

## Stage 1 – Lay Domain-Driven Foundations (Week 2–3)
- [ ] Introduce layered structure (`domain/`, `application/`, `infrastructure/`) for authenticated modules.
- [ ] Collapse FastAPI routing into unified `backend/api` package consuming application services.
- [ ] Document bounded contexts and ownership boundaries (Commodity Ops, Trading, Risk, Finance, Logistics, Partners, AI).

## Stage 2 – Platform Plumbing (Week 4–6)
- [ ] Add message bus abstraction and initial event contracts for auth, onboarding, and trading workflows.
- [ ] Establish observability stack (metrics, logs, tracing) and centralized configuration service.
- [ ] Implement tenancy/caching policy primitives aligned with global rollout goals.

## Stage 3 – Incremental Service Extraction (Week 7–10)
- [ ] Split high-value contexts (Identity, Partner Management, Trading) into deployable services behind an API gateway.
- [ ] Introduce service discovery, gateway load balancing, and background worker infrastructure.
- [ ] Harden CI/CD with contract tests, health checks, and automated migrations per service.

## Stage 4 – 2040-Grade Capabilities (Week 10+)
- [ ] Build commodity-specific engines (cotton, sugar, oilseeds, metals, etc.) driven by regional compliance rules.
- [ ] Deliver AI/analytics pipelines (model registry, feature store, inference services, data lake ingestion).
- [ ] Implement real-time bidding, trade finance, logistics orchestration, branch accounting, and governance automation.
- [ ] Design global HA/DR strategy, RBAC 3.0, and compliance automation.
