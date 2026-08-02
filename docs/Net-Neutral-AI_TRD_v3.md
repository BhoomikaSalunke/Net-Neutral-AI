# Technical Requirements Document (TRD)
## Net-Neutral-AI — v3 Rebuild
**Repo:** github.com/Bhoomika-Salunke/Net-Neutral-AI
**Status:** Pre-implementation
**Timeline:** Open-ended

---

## 1. Purpose & Scope

Full rebuild of the federated learning coordinator/client system. This is not an iteration on v2 — v2 is being abandoned rather than debugged, because its failures were architectural (state living only in process memory) rather than isolated bugs. This TRD encodes the constraints that caused v2 to fail as hard requirements for v3, so they cannot be silently reintroduced.

**Explicitly out of scope for v3:**
- Supabase (removed in the V2 TRD/PRD update; not reintroduced here)
- Any client-side GUI 
- WebSockets for coordinator↔client round sync 
- Fly.io as a deployment target (evaluated, rejected — no free tier as of 2026)

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | FastAPI (Python) | Replaces Flask |
| Frontend | HTML / CSS / JS | Served by the coordinator; browser-only, no client-side GUI |
| Database | PostgreSQL via Neon (free tier) | Chosen over Supabase — no bundled auth/storage needed, no forced weekly pause; over Render's own free Postgres — no 30-day expiry |
| ORM | SQLAlchemy (async) + `asyncpg` driver | 
| Migrations | Alembic | Every schema change goes through a migration, not manual edits |
| Deployment | Render (free Hobby web service) | 512MB RAM ceiling, ephemeral filesystem, cold start after idle — treated as a hard constraint, not an inconvenience |
| CI/CD | Pipeline that tests, then deploys | Test gate must run training against the 40K-row dataset before any deploy is allowed to proceed |
| Config | `.env` file locally → environment variables in deployment | Same variable names in both; |

---

## 3. Non-Negotiable Architecture Rule

> **Anything that must survive a process restart does not live in a Python variable.**

This is the direct fix for v2's core failure: `current_round`, `round_status`, `registered_clients`, and `submitted_weights` lived only in Flask module-level globals. A Render free-tier restart (idle spin-down, redeploy, or an OOM kill during evaluation) silently reset all of it, and the client-side polling loop (`round > current_round`) could never recover once the server's round number went backward.

**Requirement:** the following must be persisted in Postgres, not held only in memory:
- Current round number and round status (per session)
- Registered clients and their live status (active / missed-round / disconnected)
- Submission tracking (who has submitted for the current round)
- Session identity 

In-memory variables are permitted only for data that is disposable if lost (e.g., an in-flight request's local computation) — never for anything another request or another process needs to see.

---

## 4. Coordinator ↔ Client Protocol

### 4.1 Roles
- **Coordinator**: single persistent FastAPI service, deployed on Render. Serves both the JSON API and the browser dashboard (HTML/CSS/JS) from the same app.
- **Client**: `client.py`, runs locally on each participant's own machine. Never deployed. Connects out to the coordinator. Never receives or transmits raw training data to the coordinator — only shard assignments (from coordinator to client) and model weights (from client to coordinator).

### 4.2 Session Identity
Every time the coordinator starts a new training session, it generates a `session_id` and persists it. This is included in every client-facing response (`/register`, `/status`).

**Requirement:** clients must store `session_id` alongside any locally cached data shard, and must treat a cached shard as valid **only if its stored `session_id` matches the coordinator's current one.** This is the direct fix for the v2 bug where a client with a stale cached shard file skipped the "wait for coordinator session start" step entirely and began training with no session active.

### 4.3 Client Interface: Terminal Only
`client.py` remains a plain terminal script. No client-side GUI, web page, or wrapped runtime.

**Rationale:** the last confirmed-stable test run (coordinator + 3 clients, terminal-only) broke specifically after a GUI was introduced. The cause of that break was never fully isolated, so v3 removes the variable entirely rather than carrying an unresolved risk forward. Central visibility into client status is provided via the coordinator dashboard, fed by clients reporting their state back to the coordinator — not by exposing each client's raw terminal.

### 4.4 Real-Time Communication
- **Coordinator → browser dashboard:** SSE (Server-Sent Events). One-way by nature, matches the need (dashboard only ever receives updates), already proven to work in v2.
- **Coordinator ↔ client (round sync):** HTTP polling, not WebSockets. Clients may be on arbitrary home networks; a long-lived WebSocket connection is more exposed to router/NAT timeouts than a periodic status check, and polling was never the source of any v2 failure — no reason to add the complexity.

### 4.5 Liveness & Disconnect Handling
- Client `last_seen` is updated on every client-initiated request (`/register`, `/submit`), plus a lightweight `/heartbeat` ping sent periodically during training.
- At each round boundary, if a registered client has not submitted within `round_timeout_seconds`, it is marked **missed** for that specific round in the database. Aggregation proceeds without them — this is also the fix for the coordinator hanging indefinitely waiting for a client that will never submit.
- A client is marked **disconnected** (not just missed-one-round) only once `last_seen` exceeds a longer threshold (e.g., no heartbeat across 2+ round-lengths) — a single missed round does not permanently remove a client.
- **On disconnect (not on a single missed round):** the coordinator hard-deletes all transient artifacts tied to that client — temp weight files on disk, in-session tracking entries, shard assignment records. What is **retained permanently**: the client's participation/credit history up to the point they left (audit trail + leaderboard data). Transient working data is deleted; earned credit history is not.

---

## 5. Deployment Constraints (Render Free Tier)

These are treated as hard requirements to design against, not risks to accept:
- **512MB RAM ceiling.** Evaluation/aggregation steps must be scoped with this in mind — this was the likely cause of the OOM/restart that triggered the v2 "infinite wait" bug at 20-40K rows.
- **Ephemeral filesystem.** Nothing written to local disk on the coordinator survives a restart. This is why persisted state lives in Postgres, not in a local SQLite file, on the deployed instance.
- **Cold start after idle.** The coordinator may take a few seconds to respond after a period of inactivity. Client polling logic must tolerate this without treating a slow-but-eventual response as a failure.

---

## 6. Local Development vs. Deployment Parity

- **Local:** local dev uses a real Postgres instance (recommend Docker — docker run postgres or a docker-compose.yml — rather than a second Neon branch per developer, for two reasons: it works offline, and it doesn't burn into Neon's 100 CU-hours/month free-tier budget just from routine local dev across multiple team members hitting it all day).
- **Deployed:** Postgres via Neon, same SQLAlchemy models, connection string swapped via config only — no code changes required to move from local to deployed.
- Schema changes go through Alembic in both environments identically.
- Neon's branching feature as the tool for testing schema migrations against a Postgres instance that mirrors production data before merging to the main branch

---

## 7. Configuration Management

- Local development: values hardcoded in a `.env` file (not committed to the repo — `.gitignore`'d), loaded via `pydantic-settings`.
- Deployment: the same variable names are set as environment variables on Render (and Neon connection string, session secrets, etc.) — no code path differs between the two, only where the values come from.

---

## 8. Data Model (carried forward from v2, extended)

Base schema (from v2, retained):
- `clients(id, client_id, ip_add, reg_at, last_seen, is_active)`
- `rounds(id, round_number, started_at, completed_at, clients_submitted, global_acc, acc_delta)`
- `credits(id, client_id, round, samples_trained, time_seconds, points_earned, timestamp)` — FK to `clients.client_id` and `rounds.round_number`

**Required additions for v3:**
- `sessions` table: `session_id`, `started_at`, `current_round`, `round_status` — the persisted replacement for v2's in-memory globals.
- Per-round client status: a way to record `submitted` / `missed` / `disconnected` per client per round (either a status column on a round-participation table, or extending `credits`/a new join table.


---

