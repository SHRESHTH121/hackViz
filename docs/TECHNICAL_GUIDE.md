# hackViz — Technical Guide

Detailed reference for hackViz. For the project overview, requirements and setup see the
[main README](../README.md).

**Contents:** 1. Project structure · 2. Live demonstration procedure · 3. How the analysis works · 4. API · 5. Privacy & security · 6. Known limitations · 7. Tests

## 1. Project structure

```
hackviz/
├── backend/                  FastAPI + SQLAlchemy 2 + psycopg 3
│   ├── app/
│   │   ├── main.py           app, CORS, startup (schema + dataset import + worker)
│   │   ├── config.py         env settings (PostgreSQL mandatory, Ollama must be localhost)
│   │   ├── database.py       engine/session/transactions
│   │   ├── seed.py           idempotent dataset import  (python -m app.seed [--reset])
│   │   ├── models/           Employee, ActivityLog, Anomaly, AnalysisState, ExtensionSession
│   │   ├── schemas/          request validation + strict LLM response schema
│   │   ├── routes/           system, employees, activity, anomalies/analysis, export, extension
│   │   └── services/         ollama_client, analyzer, indicators, domain_catalog, worker
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 React 18 + Vite + Lucide + Recharts (dark SOC-style dashboard)
│   └── src/{pages,components,services,hooks}
├── extension/                Chrome Manifest V3 extension (popup pairing, webNavigation, downloads)
├── data/
│   ├── generate_dataset.py   reproducible synthetic CERT-style generator (seeded)
│   └── generated/            employees.json, historical_activity.csv, manifest.json
├── tests/                    pytest suites + tests/e2e (real Chrome + extension end-to-end)
├── scripts/                  PowerShell helpers (start-*, run-tests)
├── docs/                     project documentation (see below), incl. TEST_RESULTS.md
└── README.md
```

## 2. Live demonstration procedure

1. Start PostgreSQL (Windows service `postgresql-x64-16` starts automatically), Ollama, backend, frontend.
2. Open <http://localhost:5173>. The dashboard shows the 10 fictional employees, the six summary
   cards and charts built from the synthetic history. Risk status is **Not assessed** until a real
   analysis has run.
3. Click **EMP002 — Rohan Sharma (SDE1)** to open the profile (historical timeline, activity log).
4. Optionally click **Add employee** and create e.g. `EMP011 / Finance Analyst`.
5. Pair the extension with `EMP002` (or the new employee). The *Monitoring Status* page now shows the
   pairing; it switches to *transmitting* only once events actually arrive.
6. Browse in Chrome: visit several websites, download a sample file, open an external service.
7. Watch the events appear in **Live Activity** (3 s refresh) and the employee profile.
8. After 5 new live events (or 90 s of inactivity) the background worker runs the analysis
   automatically — or click **Analyze Now** on the profile. A spinner shows inference is running
   (typically 20–90 s on CPU).
9. The assessment appears on the profile and in **Anomaly Alerts**: risk level, confidence
   estimate, the model's explanation, recommended action, analysis timestamp, model name,
   supporting indicators, and the full analyzed sequence plus the raw model response.
10. Click any evidence ID chip (`#1234`) to open the original PostgreSQL activity record.
11. Repeat with another employee/role (e.g. pair `EMP011` Finance Analyst and download a file then
    open a file-sharing site) to show role-aware assessment.
12. Export CSV from the dashboard (all activity) or the profile (one employee).

## 3. How the analysis works

1. `POST /api/activity` validates and stores the event (never waits for the LLM).
2. A single background worker thread finds employees with unanalyzed **live** events
   (`id > analysis_state.last_analyzed_event_id`) and triggers when ≥ `ANALYSIS_BATCH_SIZE`
   new events exist or the newest one is older than `ANALYSIS_IDLE_SECONDS`.
3. Context sent to the model (compact, ≤ ~40 records):
   employee role/department and role-expected site categories → **historical baseline summary**
   (period, events/day, downloads/day, usual hours, top domains, categories, removable-media and
   external-email counts) → up to 15 **preceding records** → the **new live records** (≤ 35)
   → **rule-based supporting indicators**.
4. Indicators (hints only): download bursts, sensitive-looking download/copy followed by
   file-sharing or personal-email activity, sensitive systems outside the role, removable media +
   copies, job-search + data movement, off-hours data movement (off-hours alone is never flagged),
   download volume vs baseline, unfamiliar domains vs history, attachments to personal email.
5. The system prompt contains the cautious instructions from the project brief plus a short
   **risk rubric** (low = explained by role/history; medium = unusual combination or moderate
   indicator with plausible explanations; high = strong indicator not explained by role/history).
   The rubric only defines the scale - the model decides. Ollama is called with a JSON schema
   (`format`), temperature 0.1. The answer is validated:
   `risk_level ∈ {low, medium, high}`, `0 ≤ confidence ≤ 1`, `is_anomaly=false ⇒ low`,
   `is_anomaly=true ⇒ medium/high`. Evidence IDs not among the supplied records are removed and the
   removal is recorded; an anomaly without any valid evidence is rejected. One corrective retry is
   allowed, otherwise the analysis fails.
6. On success the assessment and the cursor update are committed in **one transaction**. On any
   failure (Ollama down, model missing, timeout, invalid JSON) nothing is saved, the cursor does not
   move, the error is shown in the UI and the batch is retried with back-off — events are never skipped.
7. Manual *Analyze Now* with no new live events analyzes the latest 35 records; re-running on an
   unchanged window returns the existing assessment (duplicate prevention) unless **Re-run** is used.

## 4. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | backend + PostgreSQL health |
| GET | `/api/status` | backend, PostgreSQL, Ollama, model, worker, extension pairing/transmission |
| GET | `/api/stats` | dashboard counters and chart data |
| GET/POST | `/api/employees` | list (with counts, last activity, risk) / create |
| GET | `/api/employees/{id}` | profile, latest assessment, analysis state/job |
| GET | `/api/employees/{id}/activity` | filters: `source`, `event_type`, `q`, `limit`, `offset` |
| GET | `/api/employees/{id}/anomalies` | assessment history |
| GET | `/api/employees/{id}/timeline` | daily counts by source + event types |
| POST | `/api/activity` | ingest one live event |
| POST | `/api/activity/batch` | ingest up to 100 queued events (per-event results) |
| GET | `/api/activity` , `/api/activity/{event_id}` | feed / single record |
| POST | `/api/analyze/{employee_id}` | queue Analyze Now (`?force=true`, `?wait=true`) |
| GET | `/api/analysis/status` | worker state |
| GET | `/api/anomalies` , `/api/anomalies/{id}` | alerts; detail includes evidence + analyzed records + raw output |
| GET | `/api/export/activity.csv[?employee_id=EMP001]` | CSV export |
| POST | `/api/extension/pair` , `/heartbeat` , `/unpair` ; GET `/api/extension/sessions` | extension pairing |

## 5. Privacy & security

* The extension collects **only** top-level navigation URLs (query string and fragment removed),
  domains, timestamps, tab id/transition type, and completed downloads (source URL without query,
  file *name* only, size, MIME). It never reads page content, titles, form data, keystrokes,
  cookies, credentials, tokens or email contents. Nothing is collected without a valid pairing and
  an explicit monitoring-notice confirmation; **Disconnect** stops collection immediately.
* Pairing verifies the employee in PostgreSQL and issues a session token; events with a revoked
  token or for a different employee are rejected.
* Input validation: employee ID format, duplicate IDs, event types, http(s) URLs only,
  URL ≤ 2048 chars, metadata key/value limits, timestamps not in the future / older than 30 days,
  duplicate transmissions (`client_event_id`) ignored. SQLAlchemy parameterized queries only.
  CSV export neutralises spreadsheet formula injection.
* `DATABASE_URL` must be PostgreSQL (SQLite or anything else is refused at startup);
  `OLLAMA_URL` must be localhost.
* Visiting an upload or file-sharing page is never described as proof of an upload; the prompt and
  indicator texts say so explicitly.

## 6. Known limitations

* Confidence is the model's subjective estimate, not a calibrated probability. A 3B model can be
  inconsistent; every alert keeps its raw output, inputs and indicators for human verification.
* CPU inference takes ~20–90 s per analysis; analyses run one at a time.
* The extension cannot see uploads, clipboard, other browsers or non-browser activity; historical
  logon/file/USB/email records exist only in the synthetic dataset.
* Downloads served from `blob:`/`data:` URLs are attributed to the referring page.
* Chrome MV3 service workers can be suspended; queued events are persisted in `chrome.storage`
  and flushed on the next event or the 30-second alarm.
* No authentication on the dashboard/API (local single-analyst prototype bound to 127.0.0.1).

## 7. Tests

```powershell
.\scripts\run-tests.ps1             # all tests incl. real Ollama inference (uses database hackviz_test)
.\scripts\run-tests.ps1 -SkipOllama
cd tests\e2e; npm install; node extension_e2e.mjs   # real Chrome + extension end-to-end (needs backend + frontend running)
```

See **[TEST_RESULTS.md](TEST_RESULTS.md)** for the tests that were actually executed and their output.
