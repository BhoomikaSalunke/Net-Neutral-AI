x# Product Requirements Document (PRD)
## Net-Neutral-AI — v3 Rebuild
**Repo:** github.com/Janhvesh-Patil/Net-Neutral-AI
**Status:** Pre-implementation
**Companion doc:** Net-Neutral-AI_TRD_v3.md (implementation-level detail lives there, not here)

---

## 1. Problem Statement

Training a machine learning model usually needs either a lot of centralized compute, or centralized access to everyone's raw data. Net-Neutral-AI lets multiple contributors train a shared model collaboratively, using their own machines, without any contributor's raw data ever leaving their device. A central coordinator organizes the process: it distributes data shards and model weights out, collects trained weight updates back, and merges them into a progressively-improving global model — but it never sees, requests, or stores anyone's raw training data.

---

## 2. Goals for v3

- A federated training session that multiple independently-run clients can join, train through to completion, and have that completion be trustworthy (no silent hangs, no phantom resets, no clients training against a session that hasn't started).
- A coordinator that degrades gracefully when a client drops out mid-session, instead of hanging indefinitely.
- A live view (dashboard) of session progress that a non-technical observer (e.g., a hackathon judge, or a teammate not actively debugging) can watch and understand.
- A credit/leaderboard system that fairly reflects actual contribution (rounds completed, samples trained), and correctly stops crediting a client the moment they're no longer meaningfully participating.

## 3. Non-Goals for v3

- Supporting arbitrary/unknown ML model architectures — the system is built and tuned around the existing TransformerClassifier/FedAvg setup, not a general-purpose FL framework.
- User authentication or account systems (Supabase-style auth was explicitly removed from scope in the V2 update and is not being reintroduced).
- A polished client-side application — the client remains a terminal tool for contributors, not a consumer product.

---

## 4. Users / Roles

### 4.1 Coordinator Operator (you)
Starts and monitors a training session from the dashboard. Needs to see, at a glance: how many clients are connected, what round is active, current global accuracy, and which clients (if any) have dropped or are lagging.

### 4.2 Client Contributor (teammates / hackathon participants)
Runs `client.py` on their own machine. Needs: a clear signal of what's happening (waiting for session, downloading shard, training, submitting, waiting for next round) via terminal output, and confidence that their raw data never leaves their machine.

### 4.3 Observer (dashboard viewer)
Anyone with the coordinator's URL who wants to watch training progress — not a participant, read-only.

---

## 5. Core Features

### 5.1 Session Lifecycle
- Operator starts a session from the dashboard.
- Clients discover and join an active session (or wait, correctly, if no session is active — this is the direct fix for the v2 bug where clients would train regardless of session state.
- Session proceeds through configured rounds; each round: shard/weight distribution → local training → submission → aggregation → evaluation → next round or completion.

### 5.2 Data Sharding
- Coordinator splits the uploaded training dataset into shards, one per client, at session start.
- A client only ever receives its own shard — never another client's, never the full dataset.

### 5.3 Distributed Training & Aggregation
- Clients train locally for a configured number of epochs, then submit weight updates (not raw data) back to the coordinator.
- Coordinator aggregates submitted weights via FedAvg, evaluates the resulting global model, and reports accuracy/accuracy-delta for the round.

### 5.4 Live Monitoring Dashboard
- Real-time view of: current round, connected/active clients, per-client status, global accuracy trend across rounds.
- Pushed via SSE — updates appear without the viewer refreshing.

### 5.5 Credit & Leaderboard
- Clients earn credit per round based on samples trained and time spent.
- A client's credit history is permanent and does not get erased if they later disconnect.

### 5.6 Disconnect Handling
- A client that misses a single round (network hiccup, etc.) is marked as having missed that round; the session continues without waiting on them, and they may rejoin.
- A client that stops responding for a longer window is marked disconnected; the coordinator purges their session-specific working data (shard assignment, temp weight files) but **their earned credit/participation history is retained** — this is a product requirement, not just a cleanup detail: a contributor who trained honestly for three rounds and then lost connection should not lose credit for those three rounds.

---

## 6. Success Criteria

- A full training session completes successfully with 3+ clients on 3+ separate physical machines, on separate networks, using the full 40K-row dataset — not a small sample, not a single machine.
- If a client is deliberately killed mid-session (simulating a crash), the session continues and completes for the remaining clients, and the disconnected client's status is correctly reflected in the dashboard and database.
- No manual restart of the coordinator is ever required to "unstick" a session — if the process does restart (e.g., a Render redeploy), the session resumes from persisted state rather than resetting.

---

## 7. Assumptions & Constraints

- Deployment target is Render's free tier: 512MB RAM, ephemeral filesystem, cold start after idle. The product's reliability claims are scoped to operating within these limits, not assuming unlimited compute.
- Team availability is irregular (open-ended timeline, no fixed sprint cadence) — this shaped the database choice (Neon over Supabase, to avoid an auto-pause tripping up an infrequently-active project) and should be kept in mind for any other "must stay warm" assumptions in future feature decisions.

---
