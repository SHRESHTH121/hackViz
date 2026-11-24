"""
hackViz - Synthetic CERT-style dataset generator.

Generates a FICTIONAL employee directory and a FICTIONAL historical activity log
in the spirit of the CERT Insider Threat datasets (logon, device, file, email,
http events).  Every person, company, host and file in this output is invented.

The generator is fully deterministic: the same --seed and --end-date always
produce byte-identical output files.

It does NOT produce anomaly labels, alerts or model outputs.  Some employees
simply behave in ways that a reviewer may or may not consider unusual; deciding
that is the job of the analysis pipeline (rules + local LLM) at runtime.

Usage:
    python data/generate_dataset.py                       # defaults
    python data/generate_dataset.py --seed 42 --days 28 --end-date 2026-11-20
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

DATASET_LABEL = "Fictional CERT-style synthetic data (hackViz)"
ORG = "Corvane Technologies (fictional)"
ORG_TZ = timezone(timedelta(hours=5, minutes=30))  # IST
EMAIL_DOMAIN = "corvane.example"

EMPLOYEES = [
    {"employee_id": "EMP001", "name": "Aarav Mehta", "role": "HR Executive", "department": "Human Resources",
     "profile": {"pc": "PC-1041", "location": "Pune", "hire_date": "2021-03-15", "work_start": "09:30", "work_end": "18:30"}},
    {"employee_id": "EMP002", "name": "Rohan Sharma", "role": "Software Developer (SDE1)", "department": "Engineering",
     "profile": {"pc": "PC-2210", "location": "Bengaluru", "hire_date": "2024-07-01", "work_start": "10:00", "work_end": "19:00"}},
    {"employee_id": "EMP003", "name": "Priya Kapoor", "role": "Software Developer (SDE2)", "department": "Engineering",
     "profile": {"pc": "PC-2217", "location": "Bengaluru", "hire_date": "2022-01-10", "work_start": "10:00", "work_end": "19:00"}},
    {"employee_id": "EMP004", "name": "Kabir Malhotra", "role": "Finance Analyst", "department": "Finance",
     "profile": {"pc": "PC-3102", "location": "Mumbai", "hire_date": "2020-09-21", "work_start": "09:30", "work_end": "18:30"}},
    {"employee_id": "EMP005", "name": "Ananya Verma", "role": "Management Intern", "department": "Management",
     "profile": {"pc": "PC-4407", "location": "Gurugram", "hire_date": "2026-06-02", "work_start": "09:30", "work_end": "18:00"}},
    {"employee_id": "EMP006", "name": "Arjun Bhatia", "role": "Project Manager", "department": "Management",
     "profile": {"pc": "PC-4402", "location": "Gurugram", "hire_date": "2019-11-04", "work_start": "09:00", "work_end": "18:30"}},
    {"employee_id": "EMP007", "name": "Ishita Rao", "role": "System Administrator", "department": "IT",
     "profile": {"pc": "PC-5001", "location": "Hyderabad", "hire_date": "2018-05-14", "work_start": "09:00", "work_end": "18:00"}},
    {"employee_id": "EMP008", "name": "Vivaan Khanna", "role": "Data Analyst", "department": "Analytics",
     "profile": {"pc": "PC-6120", "location": "Bengaluru", "hire_date": "2023-02-20", "work_start": "09:30", "work_end": "18:30"}},
    {"employee_id": "EMP009", "name": "Meera Sethi", "role": "Sales Executive", "department": "Sales",
     "profile": {"pc": "PC-7033", "location": "Delhi", "hire_date": "2022-08-08", "work_start": "09:30", "work_end": "18:30"}},
    {"employee_id": "EMP010", "name": "Aditya Nair", "role": "Research Intern", "department": "Research",
     "profile": {"pc": "PC-8012", "location": "Chennai", "hire_date": "2026-07-15", "work_start": "10:00", "work_end": "18:30"}},
]
for _e in EMPLOYEES:
    first, last = _e["name"].lower().split(" ", 1)
    _e["email"] = f"{first}.{last}@{EMAIL_DOMAIN}"

# --------------------------------------------------------------------------- #
# Behaviour pools (domain, path) per role.  Internal hosts are fictional.
# --------------------------------------------------------------------------- #
COMMON_WEB = [
    ("intranet.corvane.internal", "/home"), ("intranet.corvane.internal", "/news"),
    ("outlook.office.com", "/mail/"), ("teams.microsoft.com", "/"),
    ("www.google.com", "/search"), ("calendar.google.com", "/calendar/"),
    ("wiki.corvane.internal", "/spaces/company"), ("timesofindia.indiatimes.com", "/"),
    ("www.youtube.com", "/watch"), ("www.linkedin.com", "/feed/"),
]
ROLE_WEB = {
    "EMP001": [("hr.corvane.internal", "/employees"), ("hr.corvane.internal", "/onboarding"),
               ("hr.corvane.internal", "/leave-requests"), ("payroll.corvane.internal", "/reports/monthly"),
               ("www.naukri.com", "/recruiter/search"), ("www.linkedin.com", "/talent/search"),
               ("docs.google.com", "/forms/"), ("www.shrm.org", "/resources")],
    "EMP002": [("github.com", "/corvane/api-gateway"), ("github.com", "/corvane/api-gateway/pulls"),
               ("stackoverflow.com", "/questions"), ("docs.python.org", "/3/library/"),
               ("developer.mozilla.org", "/en-US/docs/Web/JavaScript"), ("jira.corvane.internal", "/browse/API"),
               ("git.corvane.internal", "/platform/api-gateway"), ("pypi.org", "/project/"),
               ("www.npmjs.com", "/package/"), ("fastapi.tiangolo.com", "/tutorial/")],
    "EMP003": [("github.com", "/corvane/payments-service"), ("github.com", "/corvane/payments-service/pulls"),
               ("stackoverflow.com", "/questions"), ("git.corvane.internal", "/platform/payments"),
               ("jira.corvane.internal", "/browse/PAY"), ("ci.corvane.internal", "/pipelines"),
               ("docs.docker.com", "/reference/"), ("kubernetes.io", "/docs/"),
               ("console.aws.amazon.com", "/cloudwatch/"), ("go.dev", "/doc/")],
    "EMP004": [("finance.corvane.internal", "/ledger"), ("finance.corvane.internal", "/reports/quarterly"),
               ("erp.corvane.internal", "/accounts-payable"), ("www.moneycontrol.com", "/markets/"),
               ("www.investing.com", "/currencies/"), ("www.rbi.org.in", "/Scripts/"),
               ("docs.google.com", "/spreadsheets/"), ("payroll.corvane.internal", "/cost-centres")],
    "EMP005": [("intranet.corvane.internal", "/projects"), ("docs.google.com", "/presentation/"),
               ("jira.corvane.internal", "/plans"), ("www.coursera.org", "/learn/"),
               ("miro.com", "/app/board/"), ("www.notion.so", "/"), ("www.canva.com", "/design/")],
    "EMP006": [("jira.corvane.internal", "/plans"), ("jira.corvane.internal", "/browse/PAY"),
               ("confluence.corvane.internal", "/display/PMO"), ("docs.google.com", "/spreadsheets/"),
               ("miro.com", "/app/board/"), ("www.smartsheet.com", "/"), ("github.com", "/corvane/payments-service/issues")],
    "EMP007": [("admin.corvane.internal", "/users"), ("admin.corvane.internal", "/groups"),
               ("portal.azure.com", "/#home"), ("console.aws.amazon.com", "/iam/"),
               ("monitor.corvane.internal", "/grafana/d/infra"), ("ad.corvane.internal", "/audit"),
               ("learn.microsoft.com", "/en-us/windows-server/"), ("www.reddit.com", "/r/sysadmin/"),
               ("backup.corvane.internal", "/jobs")],
    "EMP008": [("dwh.corvane.internal", "/query"), ("bi.corvane.internal", "/dashboards"),
               ("www.kaggle.com", "/datasets"), ("pandas.pydata.org", "/docs/"),
               ("stackoverflow.com", "/questions"), ("colab.research.google.com", "/"),
               ("public.tableau.com", "/app/discover"), ("github.com", "/corvane/analytics-notebooks")],
    "EMP009": [("crm.corvane.internal", "/leads"), ("crm.corvane.internal", "/opportunities"),
               ("www.linkedin.com", "/sales/"), ("www.zoho.com", "/crm/"),
               ("docs.google.com", "/presentation/"), ("www.justdial.com", "/"), ("maps.google.com", "/")],
    "EMP010": [("scholar.google.com", "/scholar"), ("arxiv.org", "/abs/"), ("www.researchgate.net", "/publication/"),
               ("research.corvane.internal", "/projects/lidar"), ("ieeexplore.ieee.org", "/document/"),
               ("colab.research.google.com", "/"), ("github.com", "/corvane-research/sensor-fusion")],
}
ROLE_APPS = {
    "EMP001": ["Outlook", "Excel", "Word", "Teams", "Chrome"],
    "EMP002": ["VS Code", "Windows Terminal", "Docker Desktop", "Chrome", "Teams", "Postman"],
    "EMP003": ["IntelliJ IDEA", "Windows Terminal", "Docker Desktop", "Chrome", "Teams"],
    "EMP004": ["Excel", "Outlook", "SAP GUI", "Chrome", "Teams"],
    "EMP005": ["PowerPoint", "Excel", "Teams", "Chrome"],
    "EMP006": ["Outlook", "Teams", "Excel", "Chrome", "MS Project"],
    "EMP007": ["PowerShell", "Remote Desktop", "PuTTY", "Chrome", "Teams", "Wireshark"],
    "EMP008": ["Jupyter", "Excel", "Power BI", "Chrome", "Teams"],
    "EMP009": ["Outlook", "Teams", "Chrome", "PowerPoint"],
    "EMP010": ["Jupyter", "MATLAB", "Chrome", "Teams"],
}
ROLE_FILES = {
    "EMP001": ["\\\\fs01\\hr\\onboarding\\checklist_{n}.docx", "\\\\fs01\\hr\\policies\\leave_policy.pdf",
               "\\\\fs01\\hr\\recruitment\\candidates_week{n}.xlsx"],
    "EMP002": ["C:\\dev\\api-gateway\\src\\routes_{n}.py", "C:\\dev\\api-gateway\\README.md",
               "\\\\fs01\\eng\\design\\gateway_rfc.md"],
    "EMP003": ["C:\\dev\\payments\\service\\ledger_{n}.go", "\\\\fs01\\eng\\design\\payments_arch.pdf",
               "C:\\dev\\payments\\deploy\\values.yaml"],
    "EMP004": ["\\\\fs01\\finance\\reports\\monthly_close_{n}.xlsx", "\\\\fs01\\finance\\budget\\fy27_draft.xlsx",
               "\\\\fs01\\finance\\ap\\invoices_batch_{n}.pdf"],
    "EMP005": ["\\\\fs01\\mgmt\\interns\\task_tracker.xlsx", "\\\\fs01\\mgmt\\decks\\market_scan_{n}.pptx"],
    "EMP006": ["\\\\fs01\\pmo\\status\\weekly_status_{n}.pptx", "\\\\fs01\\pmo\\plans\\roadmap_q1.xlsx",
               "\\\\fs01\\pmo\\risks\\raid_log.xlsx"],
    "EMP007": ["\\\\fs01\\it\\runbooks\\patching_{n}.md", "\\\\fs01\\it\\inventory\\assets.xlsx",
               "C:\\admin\\scripts\\backup_check.ps1"],
    "EMP008": ["\\\\fs01\\analytics\\notebooks\\churn_{n}.ipynb", "\\\\fs01\\analytics\\extracts\\sales_summary_{n}.csv"],
    "EMP009": ["\\\\fs01\\sales\\proposals\\proposal_client_{n}.docx", "\\\\fs01\\sales\\pricing\\price_list_2026.pdf"],
    "EMP010": ["\\\\fs01\\research\\lidar\\notes_{n}.docx", "\\\\fs01\\research\\papers\\draft_{n}.pdf"],
}
ROLE_DOWNLOADS = {
    "EMP001": [("hr.corvane.internal", "offer_letter_template.docx"), ("www.shrm.org", "hr_compliance_guide.pdf")],
    "EMP002": [("github.com", "api-gateway-main.zip"), ("pypi.org", "requests-2.32.3.tar.gz"),
               ("nodejs.org", "node-v22-x64.msi")],
    "EMP003": [("github.com", "payments-service-release.zip"), ("go.dev", "go1.23.windows-amd64.msi")],
    "EMP004": [("finance.corvane.internal", "trial_balance_{n}.xlsx"), ("www.rbi.org.in", "rbi_bulletin.pdf")],
    "EMP005": [("www.canva.com", "slide_template.pptx"), ("intranet.corvane.internal", "intern_handbook.pdf")],
    "EMP006": [("confluence.corvane.internal", "project_charter_{n}.pdf"), ("www.smartsheet.com", "gantt_export.xlsx")],
    "EMP007": [("learn.microsoft.com", "LAPS_x64.msi"), ("www.putty.org", "putty-64bit.msi"),
               ("backup.corvane.internal", "backup_report_{n}.csv")],
    "EMP008": [("www.kaggle.com", "retail_dataset.zip"), ("dwh.corvane.internal", "query_result_{n}.csv")],
    "EMP009": [("crm.corvane.internal", "lead_list_week{n}.csv"), ("www.zoho.com", "brochure.pdf")],
    "EMP010": [("arxiv.org", "2410.{n}v1.pdf"), ("ieeexplore.ieee.org", "paper_{n}.pdf")],
}
# How busy each person is (multiplier on base volumes).
ACTIVITY_LEVEL = {"EMP001": 0.9, "EMP002": 1.2, "EMP003": 1.1, "EMP004": 1.0, "EMP005": 0.8,
                  "EMP006": 1.0, "EMP007": 1.3, "EMP008": 1.0, "EMP009": 0.9, "EMP010": 0.8}


class Gen:
    def __init__(self, seed: int, end_date: date, days: int):
        self.rng = random.Random(seed)
        self.end_date = end_date
        self.days = days
        self.events: list[dict] = []

    # ---------------- helpers ----------------
    def at(self, d: date, hh: int, mm: int, ss: int = 0) -> datetime:
        return datetime.combine(d, time(hh % 24, mm % 60, ss % 60), tzinfo=ORG_TZ)

    def rand_time(self, d: date, start_h: float, end_h: float) -> datetime:
        secs = self.rng.uniform(start_h * 3600, end_h * 3600)
        return datetime.combine(d, time(0, 0), tzinfo=ORG_TZ) + timedelta(seconds=secs)

    def add(self, emp: str, ts: datetime, event_type: str, domain=None, url=None, filename=None, **meta):
        meta = {"pc": next(e["profile"]["pc"] for e in EMPLOYEES if e["employee_id"] == emp), **meta}
        self.events.append({
            "employee_id": emp,
            "timestamp": ts.astimezone(timezone.utc),
            "event_type": event_type,
            "domain": domain,
            "url": url,
            "filename": filename,
            "metadata": meta,
        })

    def fill(self, template: str) -> str:
        return template.replace("{n}", str(self.rng.randint(1, 48)))

    # ---------------- ordinary workday ----------------
    def workday(self, emp: dict, d: date):
        eid = emp["employee_id"]
        p = emp["profile"]
        sh, sm = map(int, p["work_start"].split(":"))
        eh, em = map(int, p["work_end"].split(":"))
        start = self.at(d, sh, sm) + timedelta(minutes=self.rng.randint(-25, 35))
        end = self.at(d, eh, em) + timedelta(minutes=self.rng.randint(-30, 70))
        lvl = ACTIVITY_LEVEL[eid]
        self.add(eid, start, "logon", activity="Logon")
        span_h = (end - start).total_seconds() / 3600
        day_start_h = start.hour + start.minute / 60 + 0.05
        day_end_h = day_start_h + span_h - 0.1

        # web navigation
        for _ in range(int(self.rng.randint(9, 16) * lvl)):
            pool = ROLE_WEB[eid] if self.rng.random() < 0.72 else COMMON_WEB
            dom, path = self.rng.choice(pool)
            self.add(eid, self.rand_time(d, day_start_h, day_end_h), "navigation", dom, f"https://{dom}{path}",
                     transition=self.rng.choice(["link", "typed", "auto_bookmark", "link"]))
        # application usage
        for app in self.rng.sample(ROLE_APPS[eid], k=min(len(ROLE_APPS[eid]), self.rng.randint(2, 4))):
            self.add(eid, self.rand_time(d, day_start_h, day_end_h), "app_usage", application=app,
                     duration_min=self.rng.randint(5, 140))
        # file access
        for _ in range(int(self.rng.randint(2, 6) * lvl)):
            path = self.fill(self.rng.choice(ROLE_FILES[eid]))
            self.add(eid, self.rand_time(d, day_start_h, day_end_h), "file_access", "fs01.corvane.internal"
                     if path.startswith("\\\\fs01") else None, None, path,
                     activity=self.rng.choice(["open", "open", "open", "write"]))
        # downloads (not every day)
        for _ in range(self.rng.choice([0, 0, 1, 1, 2])):
            dom, fn = self.rng.choice(ROLE_DOWNLOADS[eid])
            fn = self.fill(fn)
            self.add(eid, self.rand_time(d, day_start_h, day_end_h), "download", dom, f"https://{dom}/files/{fn}",
                     fn, file_size_kb=self.rng.randint(40, 18000))
        # email metadata (never contents)
        for _ in range(self.rng.randint(2, 6)):
            external = self.rng.random() < (0.35 if eid in ("EMP009", "EMP001") else 0.1)
            to_dom = self.rng.choice(["clientmail.example", "partner-co.example", "vendor.example"]) if external \
                else EMAIL_DOMAIN
            self.add(eid, self.rand_time(d, day_start_h, day_end_h), "email", to_dom, None, None,
                     direction="sent", recipients=self.rng.randint(1, 4),
                     attachments=self.rng.choice([0, 0, 0, 1]), size_kb=self.rng.randint(8, 900))
        self.add(eid, end, "logoff", activity="Logoff")

    # ---------------- employee-specific behaviour ----------------
    def specific(self, emp: dict, d: date, day_index: int):
        """Individual habits.  Some are perfectly legitimate for the role, a few
        are the kind of thing an investigator might want to look at.  Nothing
        here is labelled - the analysis pipeline has to work it out."""
        eid = emp["employee_id"]
        last_week = day_index >= self.days - 7
        r = self.rng.random

        if eid == "EMP004":  # Finance analyst
            if day_index >= self.days - 14 and r() < 0.5:   # job hunting lately
                dom, path = self.rng.choice([("www.naukri.com", "/jobs/finance-analyst"),
                                             ("www.linkedin.com", "/jobs/view"), ("www.indeed.co.in", "/jobs")])
                self.add(eid, self.rand_time(d, 12.5, 14.0), "navigation", dom, f"https://{dom}{path}",
                         transition="typed")
            if day_index == self.days - 3:  # an evening of bulk exports
                t = self.at(d, 20, 41)
                self.add(eid, t, "logon", activity="Logon")
                for i, fn in enumerate(["payroll_master_FY26.xlsx", "vendor_bank_accounts.csv",
                                        "salary_bands_all_staff.xlsx", "board_forecast_confidential.xlsx"]):
                    self.add(eid, t + timedelta(minutes=3 + i * 2), "file_access", "fs01.corvane.internal", None,
                             f"\\\\fs01\\finance\\restricted\\{fn}", activity="copy")
                    self.add(eid, t + timedelta(minutes=4 + i * 2), "download", "finance.corvane.internal",
                             f"https://finance.corvane.internal/export/{fn}", fn,
                             file_size_kb=self.rng.randint(900, 7000))
                self.add(eid, t + timedelta(minutes=14), "navigation", "wetransfer.com", "https://wetransfer.com/",
                         transition="typed")
                self.add(eid, t + timedelta(minutes=15), "navigation", "wetransfer.com",
                         "https://wetransfer.com/upload", transition="link")
                self.add(eid, t + timedelta(minutes=21), "email", "gmail.com", None, None, direction="sent",
                         recipients=1, attachments=2, size_kb=8400)
                self.add(eid, t + timedelta(minutes=26), "logoff", activity="Logoff")

        elif eid == "EMP005":  # Management intern browsing HR compensation pages
            if last_week and r() < 0.7:
                for path in self.rng.sample(["/compensation/salary-bands", "/employees/directory/export",
                                             "/compensation/bonus-plan", "/payroll/summary"], k=2):
                    self.add(eid, self.rand_time(d, 15.0, 17.5), "navigation", "hr.corvane.internal",
                             f"https://hr.corvane.internal{path}", transition="typed")
                if r() < 0.5:
                    self.add(eid, self.rand_time(d, 17.0, 17.9), "download", "hr.corvane.internal",
                             "https://hr.corvane.internal/export/employee_directory.csv", "employee_directory.csv",
                             file_size_kb=640)

        elif eid == "EMP007":  # Sysadmin - legitimate after-hours maintenance and USB tooling
            if d.weekday() == 3:  # Thursday patch window
                t = self.at(d, 22, 5) + timedelta(minutes=self.rng.randint(0, 20))
                self.add(eid, t, "logon", activity="Logon")
                self.add(eid, t + timedelta(minutes=2), "navigation", "admin.corvane.internal",
                         "https://admin.corvane.internal/patching", transition="typed")
                self.add(eid, t + timedelta(minutes=5), "app_usage", application="Remote Desktop", duration_min=75)
                self.add(eid, t + timedelta(minutes=8), "navigation", "monitor.corvane.internal",
                         "https://monitor.corvane.internal/grafana/d/infra", transition="link")
                self.add(eid, t + timedelta(minutes=90), "logoff", activity="Logoff")
            if r() < 0.25:
                t = self.rand_time(d, 11, 16)
                self.add(eid, t, "removable_media", activity="connect", device="IT-tools USB (asset IT-0042)")
                self.add(eid, t + timedelta(minutes=12), "removable_media", activity="disconnect",
                         device="IT-tools USB (asset IT-0042)")

        elif eid == "EMP010":  # Research intern
            if day_index == self.days - 5:  # late-night copy session to removable media
                t = self.at(d, 23, 12)
                self.add(eid, t, "logon", activity="Logon")
                self.add(eid, t + timedelta(minutes=1), "removable_media", activity="connect",
                         device="Generic USB Mass Storage")
                for i in range(7):
                    self.add(eid, t + timedelta(minutes=2 + i), "file_access", "fs01.corvane.internal", None,
                             f"\\\\fs01\\research\\lidar\\restricted\\prototype_design_v{i + 1}.pdf",
                             activity="copy", destination="removable")
                self.add(eid, t + timedelta(minutes=11), "navigation", "mega.nz", "https://mega.nz/", transition="typed")
                self.add(eid, t + timedelta(minutes=14), "removable_media", activity="disconnect",
                         device="Generic USB Mass Storage")
                self.add(eid, t + timedelta(minutes=16), "logoff", activity="Logoff")

        elif eid == "EMP002":  # Junior dev - occasionally reads up on cloud consoles (normal learning)
            if r() < 0.15:
                self.add(eid, self.rand_time(d, 14, 17), "navigation", "console.aws.amazon.com",
                         "https://console.aws.amazon.com/lambda/", transition="link")

        elif eid == "EMP008":  # Data analyst pulls large but routine extracts
            if r() < 0.3:
                t = self.rand_time(d, 11, 16)
                for i in range(2):
                    fn = f"weekly_extract_{self.rng.randint(1, 30)}_{i}.csv"
                    self.add(eid, t + timedelta(minutes=i * 3), "download", "dwh.corvane.internal",
                             f"https://dwh.corvane.internal/export/{fn}", fn, file_size_kb=self.rng.randint(2000, 9000))

        elif eid == "EMP009":  # Sales exec uses personal cloud storage to share brochures (policy grey area)
            if r() < 0.2:
                self.add(eid, self.rand_time(d, 12, 17), "navigation", "drive.google.com",
                         "https://drive.google.com/drive/my-drive", transition="link")

    def run(self) -> list[dict]:
        start = self.end_date - timedelta(days=self.days - 1)
        for i in range(self.days):
            d = start + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            for emp in EMPLOYEES:
                if self.rng.random() < 0.05:  # occasional leave day
                    continue
                self.workday(emp, d)
                self.specific(emp, d, i)
        self.events.sort(key=lambda e: (e["timestamp"], e["employee_id"], e["event_type"]))
        return self.events


def write_outputs(events: list[dict], out_dir: Path, seed: int, end_date: date, days: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    emp_path = out_dir / "employees.json"
    act_path = out_dir / "historical_activity.csv"
    emp_path.write_text(json.dumps({"label": DATASET_LABEL, "organization": ORG, "employees": EMPLOYEES},
                                   indent=2), encoding="utf-8")
    with act_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "employee_id", "timestamp", "event_type", "domain", "url", "filename",
                    "source", "metadata_json"])
        for i, e in enumerate(events, 1):
            w.writerow([f"H{i:06d}", e["employee_id"], e["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                        e["event_type"], e["domain"] or "", e["url"] or "", e["filename"] or "",
                        "historical_cert", json.dumps(e["metadata"], sort_keys=True)])
    digest = hashlib.sha256(act_path.read_bytes() + emp_path.read_bytes()).hexdigest()
    manifest = {"label": DATASET_LABEL, "seed": seed, "end_date": end_date.isoformat(), "days": days,
                "employees": len(EMPLOYEES), "events": len(events), "sha256": digest}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def generate(seed: int = 42, end_date: date = date(2026, 11, 20), days: int = 28,
             out_dir: Path | None = None) -> dict:
    out_dir = out_dir or Path(__file__).resolve().parent / "generated"
    events = Gen(seed, end_date, days).run()
    return write_outputs(events, out_dir, seed, end_date, days)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--days", type=int, default=28, help="calendar days of history (weekends are skipped)")
    ap.add_argument("--end-date", default="2026-11-20", help="last day of history, YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="output directory (default data/generated)")
    a = ap.parse_args()
    m = generate(a.seed, date.fromisoformat(a.end_date), a.days, Path(a.out) if a.out else None)
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
