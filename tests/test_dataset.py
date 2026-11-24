"""Synthetic CERT-style dataset generation."""
import csv
import json
from datetime import date, datetime

import generate_dataset as g

EXPECTED = {
    "EMP001": ("Aarav Mehta", "HR Executive", "Human Resources"),
    "EMP002": ("Rohan Sharma", "Software Developer (SDE1)", "Engineering"),
    "EMP003": ("Priya Kapoor", "Software Developer (SDE2)", "Engineering"),
    "EMP004": ("Kabir Malhotra", "Finance Analyst", "Finance"),
    "EMP005": ("Ananya Verma", "Management Intern", "Management"),
    "EMP006": ("Arjun Bhatia", "Project Manager", "Management"),
    "EMP007": ("Ishita Rao", "System Administrator", "IT"),
    "EMP008": ("Vivaan Khanna", "Data Analyst", "Analytics"),
    "EMP009": ("Meera Sethi", "Sales Executive", "Sales"),
    "EMP010": ("Aditya Nair", "Research Intern", "Research"),
}


def test_generation_is_reproducible(tmp_path):
    a = g.generate(seed=42, end_date=date(2026, 11, 20), days=28, out_dir=tmp_path / "a")
    b = g.generate(seed=42, end_date=date(2026, 11, 20), days=28, out_dir=tmp_path / "b")
    assert a["sha256"] == b["sha256"]
    assert (tmp_path / "a" / "historical_activity.csv").read_bytes() == (tmp_path / "b" / "historical_activity.csv").read_bytes()
    c = g.generate(seed=7, end_date=date(2026, 11, 20), days=28, out_dir=tmp_path / "c")
    assert c["sha256"] != a["sha256"], "different seed should give different data"


def test_employees_and_roles(tmp_path):
    g.generate(out_dir=tmp_path)
    data = json.loads((tmp_path / "employees.json").read_text(encoding="utf-8"))
    assert "Fictional" in data["label"]
    emps = {e["employee_id"]: (e["name"], e["role"], e["department"]) for e in data["employees"]}
    assert emps == EXPECTED


def test_events_valid(tmp_path):
    m = g.generate(out_dir=tmp_path)
    rows = list(csv.DictReader((tmp_path / "historical_activity.csv").open(encoding="utf-8")))
    assert len(rows) == m["events"] and 2000 < len(rows) < 20000
    ids = set(EXPECTED)
    types = set()
    prev = None
    for r in rows:
        assert r["employee_id"] in ids
        assert r["source"] == "historical_cert"
        ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        assert datetime(2026, 10, 1).date() <= ts.date() <= date(2026, 11, 21)
        if prev:
            assert ts >= prev, "events must be chronological"
        prev = ts
        json.loads(r["metadata_json"])
        types.add(r["event_type"])
        if r["event_type"] == "email":
            assert r["url"] == "" and "subject" not in r["metadata_json"] and "body" not in r["metadata_json"]
    assert {"navigation", "download", "file_access", "app_usage", "email", "logon", "logoff", "removable_media"} <= types
    per_emp = {e: sum(1 for r in rows if r["employee_id"] == e) for e in ids}
    assert all(n > 200 for n in per_emp.values()), per_emp


def test_no_labels_or_alerts_in_dataset(tmp_path):
    g.generate(out_dir=tmp_path)
    header = (tmp_path / "historical_activity.csv").open(encoding="utf-8").readline().lower()
    for word in ("anomaly", "label", "risk", "malicious", "insider"):
        assert word not in header
