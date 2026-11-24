# hackViz — Test Results

All tests below were **actually executed** on 2026-11-24 on the development machine
(Windows 11 Pro, 16 GB RAM, CPU-only; Python 3.12.10; Node 26.13.1; PostgreSQL 16.16;
Ollama 0.40.16 with `qwen2.5:3b`; Google Chrome 158). No model response was mocked in the
inference tests: every assessment quoted here was produced by the local model.

| Suite | How it was run | Result |
|---|---|---|
| Backend / database / dataset / LLM (pytest) | `backend\.venv\Scripts\python -m pytest tests -v -s` (database `hackviz_test`) | **54 passed, 0 failed** (8 min 27 s; 9 tests use real Ollama inference) |
| Chrome extension end-to-end | `node tests/e2e/extension_e2e.mjs` (real Chrome + unpacked extension, real backend/frontend on database `hackviz`) | **27 passed, 0 failed** |
| Dashboard UI checks | `node tests/e2e/ui_check.mjs` | **8 passed, 0 failed**, no browser console errors |
| Backend restart persistence | stopped uvicorn, restarted, compared counts | **passed** |
| Frontend production build | `npx vite build` | **passed** |

Raw outputs: `tests/e2e/e2e_results.json`, screenshots in `tests/e2e/screens/`.

---

## 1. PostgreSQL (tests/test_database.py, tests/test_api.py)

| Test | Result |
|---|---|
| Connection via SQLAlchemy + **psycopg 3** to PostgreSQL 16.16 (`dialect=postgresql`, `driver=psycopg`) | PASS |
| All 5 tables created automatically (employees, activity_logs, anomalies, analysis_state, extension_sessions) | PASS |
| Exactly the 10 initial fictional employees with correct roles/departments | PASS |
| Historical import count equals CSV row count (4,891); no orphan activity rows | PASS |
| Seeding is idempotent (second run imports nothing) | PASS |
| No alerts exist after seeding (0 anomalies) | PASS |
| Employee creation, duplicate employee ID → HTTP 409 | PASS |
| Activity persistence (event stored and read back by ID) | PASS |
| Persistence across a brand-new engine/connection pool | PASS |
| Non-PostgreSQL `DATABASE_URL` (sqlite) refused at startup | PASS |
| **Real backend restart**: before = 11 employees / 4,891 hist / 9 live / 2 assessments; after restart identical, nothing re-imported, analysis cursor (4900) persisted | PASS |

## 2. Dataset (tests/test_dataset.py)

| Test | Result |
|---|---|
| Reproducible: same seed → byte-identical files (sha256 `1d5a4f21…a7f0`); different seed → different data | PASS |
| 10 employees with the required IDs, names, roles, departments; labelled "Fictional" | PASS |
| 4,891 events, all employee IDs valid, timestamps valid and chronological (2026-10-26 → 2026-11-20) | PASS |
| All 8 event types present (navigation, download, file_access, app_usage, email metadata, logon, logoff, removable_media); email rows carry no subject/body | PASS |
| No anomaly/label/risk columns in the dataset | PASS |

## 3. Backend API (tests/test_api.py)

| Test | Result |
|---|---|
| `/api/health`, `/api/status` (DB, Ollama, worker, monitoring) | PASS |
| Employee list / create / get / 404 / validation (empty ID, bad ID format, empty role, bad email, optional email) | PASS |
| Activity ingestion; **query string and fragment stripped** (`?q=secret&token=abc#frag` removed) | PASS |
| Duplicate transmission (`client_event_id`) not stored twice | PASS |
| Download filename stored as basename only (no local path) | PASS |
| Rejections: unknown employee (404), `file://` and `chrome://` URLs, unknown event type, `historical_cert` source, future timestamp, URL > 8 KB (422) | PASS |
| Batch ingestion: one malformed event does not reject the valid one | PASS |
| Activity filters, employee timeline, dashboard stats | PASS |
| CSV export: header, row count = all activity, per-employee export, unknown employee 404 | PASS |
| Extension pairing: unknown ID 404, invalid ID 422, pair → name/role, heartbeat, token cannot post for another employee (403), unpair → further events 401 | PASS |
| Analyze Now: unknown employee 404, employee with no activity 422 | PASS |

## 4. Analysis logic without the LLM (tests/test_analysis_logic.py)

| Test | Result |
|---|---|
| Valid model JSON accepted; `"HIGH"` / `"#102"` normalised | PASS |
| Rejected: risk `critical`, confidence 1.7 / −0.1, `is_anomaly=false` + high, `is_anomaly=true` + low, empty reason, null action, missing field | PASS |
| Invented evidence IDs removed and recorded in `validation_notes`; anomaly with only invented IDs rejected | PASS |
| Malformed / non-object JSON rejected | PASS |
| Indicator: sensitive download → wetransfer within 60 min = `strong`, text says an upload page is not proof | PASS |
| Single unfamiliar website → no moderate/strong indicator | PASS |
| Role awareness: admin portal is expected for System Administrator, flagged for Management Intern | PASS |
| Download burst detected; off-hours navigation alone → no indicator | PASS |
| Prompt compact (35 events < 9,000 chars) and labelled | PASS |

## 5. Ollama — real inference (tests/test_ollama.py)

| Test | Result |
|---|---|
| Ollama reachable, `qwen2.5:3b` available | PASS |
| Structured JSON returned with all required keys | PASS |
| Live batch (Finance Analyst: 3 sensitive downloads → wetransfer.com) saved; evidence ⊆ supplied records and exists in PostgreSQL; cursor advanced; repeat auto run → `skipped` | PASS |
| Role-aware: developer doing normal dev browsing saved and validated | PASS |
| Manual analysis with no new live events; identical re-run → `duplicate` (same alert returned, no new inference) | PASS |
| Empty activity: manual → `NothingToAnalyze`; auto → `skipped` | PASS |
| Timeout (0.001 s) → `OllamaTimeout`, **no alert saved, cursor not advanced** | PASS |
| Missing model → `ModelMissing`; unreachable server → `OllamaUnavailable`; status reports unreachable | PASS |
| `POST /api/analyze/EMP010?wait=true` through the background worker → alert retrievable with evidence records | PASS |

Actual model outputs from the final run (unedited excerpts):

| Employee / scenario | is_anomaly | Risk | Conf. | Time | Model reason (excerpt) |
|---|---|---|---|---|---|
| EMP004 Finance Analyst — payroll/bank/salary downloads then wetransfer.com | true | **high** | 0.85 | 108 s | "downloaded several sensitive-looking files (payroll_master_FY26.xlsx, vendor_bank_accounts.csv, salary_bands_all_staff.xlsx) within a short period and then visited a file-sharing page (wetransfer.com)…" |
| EMP002 SDE1 — GitHub, StackOverflow, Python docs, PyPI | false | **low** | 0.95 | 109 s | "consistent with their role and usual behavior… expected for a Software Developer (SDE1)." |
| EMP010 Research Intern — arxiv.org (via API) | false | **low** | — | — | "typical research-related navigation to a preprint server, which is consistent with the employee's role…" |

Additional real run with the final prompt (scratch experiment, same pipeline): EMP005 Management
Intern visiting HR salary-band/directory pages, downloading `employee_directory.csv`, then
opening personal Gmail → **medium (0.75)**: "unusual for a Management Intern role… warranting human review."

## 6. Chrome extension — end-to-end with real Chrome (tests/e2e/extension_e2e.mjs)

Puppeteer drove the installed Google Chrome 158 with the unpacked extension (loaded over the
DevTools pipe because branded Chrome no longer accepts `--load-extension`). All browsing below
was real network activity.

| Step | Result | Detail |
|---|---|---|
| Backend health / model available / 10 employees | PASS | PostgreSQL 16.16, qwen2.5:3b |
| Add employee EMP011 (Finance Analyst) | PASS | HTTP 201 |
| Extension loads (MV3 service worker running) | PASS | |
| Popup shows backend connectivity | PASS | |
| Pairing blocked until monitoring notice confirmed | PASS | |
| Invalid employee ID rejected | PASS | "Employee ID EMP999 does not exist" |
| Valid pairing; name + role from PostgreSQL | PASS | "Sara Iyer — Finance Analyst · Finance" |
| Real navigations | PASS | 7/7: example.com, wikipedia.org, python.org, github.com, developer.mozilla.org, wetransfer.com, local page with `?token=SECRET123` |
| Real downloads | PASS | `Hello-World-master.zip` (codeload.github.com), `sample_report.csv` (local server) |
| Navigation + download events in PostgreSQL | PASS | 7 navigation, 2 download (with filenames) |
| Query strings / tokens stripped | PASS | `SECRET123` never stored |
| Monitoring status = paired **and** transmitting | PASS | events_received = 9, connection online |
| Popup shows last successful transmission | PASS | 9 sent |
| Ollama analysis job completed | PASS | auto-batch triggered at 5 events, 28 s after the request |
| Assessment saved; covers the live events | PASS | alert #1: low, 0.85 |
| Evidence IDs reference real records of this employee | PASS | |
| Dashboard lists employees incl. EMP011 | PASS | |
| Alert visible in Anomaly Alerts | PASS | |
| Live activity feed shows extension events | PASS | |
| CSV export for employee matches stored activity | PASS | 9 rows |
| **No activity collected after Disconnect** | PASS | 9 → 9 |

After the E2E run the remaining 4 live events were picked up automatically by the **idle trigger**
(92 s idle) and assessed: alert #2 **medium (0.65)**, evidence `#4897` (the wetransfer.com visit).

UI checks (`ui_check.mjs`): all five pages render; clicking evidence chip `#4897` opens the original
PostgreSQL record (navigation, wetransfer.com); the expanded alert shows indicators, the analyzed
sequence and the raw model response; no console errors.

## 7. Problems found by testing and fixed

| Found | Fix |
|---|---|
| Portable PostgreSQL zip blocked by Windows Smart App Control (unsigned DLLs) | Installed the official EDB 16.16 build (signed) with the user's approval |
| First real run: Finance exfiltration-like sequence rated **low** by the model | Added a short risk rubric (low/medium/high definitions) to the system prompt; same scenario now **high**, normal developer browsing still **low** |
| Role keyword `hr` / `it ` matched inside other words | Whole-word matching |
| Developers expected `admin_infra`, hiding AD/admin-portal access | Split into `it_admin` (sensitive) and `cloud_consoles` |
| Profile "Event types" chart drew live events in the historical colour | Timeline endpoint now splits event types by source |
| Charts captured mid-animation; status pills red before first status load | Animations disabled, bar width capped; pills neutral until status known |
| Test assumed exactly 10 employees although other tests add employees | Test checks the seeded synthetic set |

## 8. Not covered by automated tests

* Manual use of the popup in your everyday Chrome profile (automation used a fresh profile; the
  extension code path is identical).
* Machine reboot (the PostgreSQL service is set to Automatic; Ollama must be started with
  `scripts\start-ollama.ps1` because it was installed as a portable copy on this machine).
* Model quality is not asserted numerically: a 3B model can still misjudge; every alert keeps its
  inputs, indicators and raw output for human verification.

After testing, the demo database `hackviz` was reset (`python -m app.seed --reset`) so the demo
starts from the 10 fictional employees, 4,891 historical records, no live events and no alerts.
