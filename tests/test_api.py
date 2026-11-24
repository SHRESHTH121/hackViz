"""Backend REST API: employees, ingestion, retrieval, export, pairing."""
import csv
import io
import uuid
from datetime import datetime, timedelta, timezone


def now_iso(offset_s=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_s)).isoformat().replace("+00:00", "Z")


def test_health_and_status(client):
    h = client.get("/api/health").json()
    assert h["database"] == "ok"
    s = client.get("/api/status").json()
    assert s["database"]["ok"] and s["database"]["engine"] == "PostgreSQL"
    assert "model_available" in s["ollama"] and s["monitoring"]["status"] in ("no_active_pairing", "paired_idle", "transmitting")


def test_list_employees(client):
    emps = client.get("/api/employees").json()
    ids = [e["employee_id"] for e in emps]
    assert all(f"EMP{i:03d}" in ids for i in range(1, 11))
    e2 = next(e for e in emps if e["employee_id"] == "EMP002")
    assert e2["role"] == "Software Developer (SDE1)" and e2["historical_activity"] > 100
    assert e2["risk_status"] in ("unassessed", "low", "medium", "high")


def test_create_employee_and_duplicate(client):
    body = {"employee_id": "emp901", "name": "  Sara   Iyer ", "role": "Finance Analyst", "department": "Finance",
            "email": "sara.iyer@corvane.example"}
    r = client.post("/api/employees", json=body)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["employee_id"] == "EMP901" and d["name"] == "Sara Iyer" and d["total_activity"] == 0
    assert client.get("/api/employees/EMP901").status_code == 200
    dup = client.post("/api/employees", json=body)
    assert dup.status_code == 409
    assert any(e["employee_id"] == "EMP901" for e in client.get("/api/employees").json())


def test_create_employee_validation(client):
    assert client.post("/api/employees", json={"employee_id": "", "name": "X Y", "role": "R1", "department": "D1"}).status_code == 422
    assert client.post("/api/employees", json={"employee_id": "BAD ID!", "name": "X Y", "role": "R1", "department": "D1"}).status_code == 422
    assert client.post("/api/employees", json={"employee_id": "EMP950", "name": "X Y", "role": "", "department": "D1"}).status_code == 422
    assert client.post("/api/employees", json={"employee_id": "EMP951", "name": "X Y", "role": "R1", "department": "D1", "email": "nope"}).status_code == 422
    ok = client.post("/api/employees", json={"employee_id": "EMP952", "name": "No Email", "role": "Intern", "department": "Ops", "email": ""})
    assert ok.status_code == 201 and ok.json()["email"] is None


def test_unknown_employee(client):
    assert client.get("/api/employees/EMP999").status_code == 404
    assert client.get("/api/employees/EMP999/activity").status_code == 404


def test_ingest_activity(client):
    ev = {"employee_id": "EMP002", "event_type": "navigation", "domain": "github.com",
          "url": "https://github.com/search?q=secret&token=abc#frag", "timestamp": now_iso(),
          "source": "chrome_extension", "client_event_id": str(uuid.uuid4()), "metadata": {"tab_id": 5, "transition": "typed"}}
    r = client.post("/api/activity", json=ev)
    assert r.status_code == 201, r.text
    eid = r.json()["id"]
    rec = client.get(f"/api/activity/{eid}").json()
    assert rec["url"] == "https://github.com/search", "query string / fragment must be stripped"
    assert rec["source"] == "chrome_extension" and rec["employee_name"] == "Rohan Sharma"
    assert rec["role"] == "Software Developer (SDE1)"
    # duplicate transmission is not stored twice
    again = client.post("/api/activity", json=ev).json()
    assert again == {"id": eid, "duplicate": True}
    feed = client.get("/api/activity", params={"source": "chrome_extension", "employee_id": "EMP002"}).json()
    assert feed["items"][0]["id"] == eid


def test_ingest_download_filename_basename_only(client):
    r = client.post("/api/activity", json={"employee_id": "EMP002", "event_type": "download",
                                          "url": "https://example.org/files/report.pdf", "filename": "C:\\Users\\me\\Downloads\\report.pdf",
                                          "timestamp": now_iso()})
    assert r.status_code == 201
    assert client.get(f"/api/activity/{r.json()['id']}").json()["filename"] == "report.pdf"


def test_ingest_rejections(client):
    base = {"employee_id": "EMP002", "event_type": "navigation", "url": "https://example.com/", "timestamp": now_iso()}
    assert client.post("/api/activity", json={**base, "employee_id": "EMP999"}).status_code == 404
    assert client.post("/api/activity", json={**base, "url": "file:///C:/secret.txt"}).status_code == 422
    assert client.post("/api/activity", json={**base, "url": "chrome://settings"}).status_code == 422
    assert client.post("/api/activity", json={**base, "event_type": "keystroke"}).status_code == 422
    assert client.post("/api/activity", json={**base, "source": "historical_cert"}).status_code == 422
    assert client.post("/api/activity", json={**base, "timestamp": now_iso(3600)}).status_code == 422
    assert client.post("/api/activity", json={**base, "url": "https://x.com/" + "a" * 9000}).status_code == 422


def test_batch_partial_failure(client):
    good = {"employee_id": "EMP003", "event_type": "navigation", "url": "https://go.dev/doc/", "timestamp": now_iso(),
            "client_event_id": str(uuid.uuid4())}
    bad = {"employee_id": "EMP003", "event_type": "navigation", "url": "ftp://nope", "timestamp": now_iso(),
           "client_event_id": str(uuid.uuid4())}
    r = client.post("/api/activity/batch", json={"events": [good, bad]})
    assert r.status_code == 201
    res = r.json()["results"]
    assert res[0]["id"] and not res[0]["duplicate"]
    assert res[1]["status"] == 422


def test_employee_activity_filters_and_timeline(client):
    r = client.get("/api/employees/EMP004/activity", params={"source": "historical_cert", "event_type": "download", "limit": 5}).json()
    assert r["total"] > 0 and all(i["event_type"] == "download" and i["source"] == "historical_cert" for i in r["items"])
    t = client.get("/api/employees/EMP004/timeline").json()
    assert t["daily"] and t["event_types"]
    s = client.get("/api/stats").json()
    assert s["total_employees"] >= 10 and s["historical_activity"] > 4000 and s["live_activity"] >= 1


def test_csv_export(client):
    r = client.get("/api/export/activity.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows[0] == ["Event ID", "Employee ID", "Employee Name", "Role", "Department", "Timestamp (UTC)",
                       "Event Type", "Domain", "URL", "Filename", "Source"]
    total = client.get("/api/stats").json()
    assert len(rows) - 1 == total["historical_activity"] + total["live_activity"]
    one = client.get("/api/export/activity.csv", params={"employee_id": "EMP001"})
    rows1 = list(csv.reader(io.StringIO(one.content.decode("utf-8-sig"))))
    assert len(rows1) > 100 and all(r[1] == "EMP001" and r[2] == "Aarav Mehta" for r in rows1[1:])
    assert client.get("/api/export/activity.csv", params={"employee_id": "EMP999"}).status_code == 404


def test_extension_pairing_flow(client):
    assert client.post("/api/extension/pair", json={"employee_id": "EMP777"}).status_code == 404
    assert client.post("/api/extension/pair", json={"employee_id": "bad id"}).status_code == 422
    p = client.post("/api/extension/pair", json={"employee_id": "emp002", "extension_version": "1.0.0"})
    assert p.status_code == 201
    pd = p.json()
    assert pd["employee_name"] == "Rohan Sharma" and pd["role"] == "Software Developer (SDE1)"
    tok = pd["session_token"]
    st = client.get("/api/status").json()["monitoring"]
    assert any(x["employee_id"] == "EMP002" for x in st["paired_extensions"])
    assert "session_token" not in client.get("/api/extension/sessions").json()[0]
    assert client.post("/api/extension/heartbeat", json={"session_token": tok}).status_code == 200
    ev = {"employee_id": "EMP002", "event_type": "navigation", "url": "https://docs.python.org/3/", "timestamp": now_iso(),
          "session_token": tok, "client_event_id": str(uuid.uuid4())}
    assert client.post("/api/activity", json=ev).status_code == 201
    sess = client.post("/api/extension/heartbeat", json={"session_token": tok}).json()
    assert sess["events_received"] == 1 and sess["last_event_at"]
    # token for EMP002 cannot be used to submit events for another employee
    assert client.post("/api/activity", json={**ev, "employee_id": "EMP004", "client_event_id": str(uuid.uuid4())}).status_code == 403
    assert client.post("/api/extension/unpair", json={"session_token": tok}).status_code == 200
    assert client.post("/api/activity", json={**ev, "client_event_id": str(uuid.uuid4())}).status_code == 401
    assert client.post("/api/extension/heartbeat", json={"session_token": tok}).status_code == 401


def test_anomaly_endpoints_404(client):
    assert client.get("/api/anomalies/999999").status_code == 404
    assert client.get("/api/activity/99999999").status_code == 404
    assert isinstance(client.get("/api/anomalies").json(), list)


def test_analyze_unknown_or_empty(client):
    assert client.post("/api/analyze/EMP999").status_code == 404
    client.post("/api/employees", json={"employee_id": "EMPTY01", "name": "No Activity", "role": "Analyst", "department": "Ops"})
    r = client.post("/api/analyze/EMPTY01")
    assert r.status_code == 422 and "no activity" in r.json()["detail"].lower()
