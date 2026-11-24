"""Lightweight domain categorisation and role expectations.

Used only to build *supporting* context for the LLM. A category mismatch is never
treated as evidence of wrongdoing on its own."""
from __future__ import annotations

from urllib.parse import urlsplit

CATEGORY_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("file_sharing", ("wetransfer.com", "mega.nz", "mega.io", "dropbox.com", "drive.google.com", "box.com",
                      "sendspace.com", "mediafire.com", "file.io", "gofile.io", "pastebin.com", "transfer.sh",
                      "onedrive.live.com", "icloud.com", "pcloud.com", "anonfiles", "filebin", "send.vis.ee")),
    ("personal_email", ("mail.google.com", "gmail.com", "mail.yahoo.com", "outlook.live.com", "proton.me",
                        "protonmail.com", "tutanota.com")),
    ("job_search", ("naukri.com", "indeed.", "monster.com", "glassdoor.", "linkedin.com/jobs", "foundit.in",
                    "instahyre.com", "wellfound.com")),
    ("hr_systems", ("hr.corvane.internal", "payroll.corvane.internal", "workday.com", "bamboohr.com",
                    "greythr.com", "shrm.org")),
    ("finance_systems", ("finance.corvane.internal", "erp.corvane.internal", "moneycontrol.com", "investing.com",
                         "rbi.org.in", "tally", "quickbooks", "sap.com")),
    ("it_admin", ("admin.corvane.internal", "ad.corvane.internal", "backup.corvane.internal",
                  "entra.microsoft.com", "admin.microsoft.com", "admin.google.com")),
    ("cloud_consoles", ("portal.azure.com", "console.aws.amazon.com", "cloud.google.com", "monitor.corvane.internal",
                        "grafana", "kibana")),
    ("dev_tools", ("github.com", "gitlab.com", "bitbucket.org", "git.corvane.internal", "ci.corvane.internal",
                   "stackoverflow.com", "stackexchange.com", "docs.python.org", "developer.mozilla.org", "npmjs.com",
                   "pypi.org", "docker.com", "kubernetes.io", "go.dev", "fastapi.tiangolo.com", "nodejs.org",
                   "react.dev", "vitejs.dev", "w3schools.com", "geeksforgeeks.org", "learn.microsoft.com",
                   "readthedocs", "rust-lang.org", "leetcode.com")),
    ("data_tools", ("dwh.corvane.internal", "bi.corvane.internal", "kaggle.com", "pandas.pydata.org",
                    "colab.research.google.com", "tableau.com", "powerbi.com")),
    ("sales_crm", ("crm.corvane.internal", "salesforce.com", "hubspot.com", "zoho.com", "justdial.com")),
    ("research", ("scholar.google.com", "arxiv.org", "researchgate.net", "ieee.org", "research.corvane.internal",
                  "springer.com", "acm.org", "nature.com")),
    ("project_mgmt", ("jira.corvane.internal", "confluence.corvane.internal", "miro.com", "smartsheet.com",
                      "notion.so", "trello.com", "asana.com")),
    ("ai_tools", ("chatgpt.com", "chat.openai.com", "claude.ai", "gemini.google.com", "copilot.microsoft.com",
                  "perplexity.ai")),
    ("collaboration", ("intranet.corvane.internal", "wiki.corvane.internal", "outlook.office.com",
                       "teams.microsoft.com", "slack.com", "zoom.us", "calendar.google.com", "docs.google.com",
                       "office.com", "sharepoint.com")),
    ("social_media", ("facebook.com", "instagram.com", "twitter.com", "x.com", "reddit.com", "linkedin.com",
                      "youtube.com", "whatsapp.com", "telegram.org", "discord.com")),
    ("search", ("google.com", "bing.com", "duckduckgo.com")),
    ("news", ("indiatimes.com", "bbc.", "cnn.com", "ndtv.com", "thehindu.com", "news.ycombinator.com")),
]

# Categories generally expected for each role family (matched by keywords in the role title).
ROLE_EXPECTATIONS: list[tuple[tuple[str, ...], set[str]]] = [
    (("developer", "engineer", "sde", "devops"), {"dev_tools", "cloud_consoles", "ai_tools", "project_mgmt"}),
    (("system administrator", "sysadmin", " it ", "network", "security"), {"it_admin", "cloud_consoles", "dev_tools", "ai_tools"}),
    (("finance", "accountant", "analyst - finance"), {"finance_systems", "data_tools"}),
    ((" hr ", "human resources", "recruit", "talent"), {"hr_systems", "job_search"}),
    (("data analyst", "data scientist", "analytics"), {"data_tools", "dev_tools", "ai_tools"}),
    (("sales", "account executive", "business development"), {"sales_crm"}),
    (("research",), {"research", "dev_tools", "data_tools", "ai_tools"}),
    (("project manager", "program manager", "scrum"), {"project_mgmt", "dev_tools"}),
    (("management", "intern", "manager"), {"project_mgmt"}),
]
UNIVERSAL = {"collaboration", "search", "news", "social_media"}
SENSITIVE_CATEGORIES = {"hr_systems", "finance_systems", "it_admin"}
SENSITIVE_FILE_WORDS = ("payroll", "salary", "salaries", "confidential", "restricted", "bank", "ssn", "passport",
                        "customer", "client_list", "employee", "directory", "forecast", "board", "secret",
                        "credential", "password", "export", "dump", "backup", "database", ".sql", "prototype",
                        "design", "source", "contract", "pii")


def categorize(domain: str | None, url: str | None = None) -> str:
    if not domain:
        return "none"
    d = domain.lower()
    if d.startswith("www."):
        d = d[4:]
    path = urlsplit(url).path.lower() if url else ""
    full = d + path
    for cat, pats in CATEGORY_PATTERNS:
        for p in pats:
            if "/" in p:
                if p in full:
                    return cat
            elif d == p or d.endswith("." + p) or (p.endswith(".") and p in d) or (p in d and "." not in p):
                return cat
    if d.endswith(".corvane.internal"):
        return "internal_other"
    return "other"


def expected_categories(role: str, department: str) -> set[str]:
    text = " " + " ".join(f"{role} {department}".lower().replace("(", " ").replace(")", " ").split()) + " "
    exp = set(UNIVERSAL)
    for keys, cats in ROLE_EXPECTATIONS:
        if any(k in text for k in keys):
            exp |= cats
    return exp


def is_sensitive_filename(name: str | None) -> bool:
    if not name:
        return False
    n = name.lower()
    return any(w in n for w in SENSITIVE_FILE_WORDS)
