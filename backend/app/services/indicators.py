"""Rule-based *supporting* indicators.

These rules never produce an alert by themselves. They point the LLM (and the
human reviewer) at event sequences worth looking at. The final assessment is
made by the local LLM, which is explicitly told the indicators may be benign."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from .domain_catalog import SENSITIVE_CATEGORIES, categorize, expected_categories, is_sensitive_filename

CORPORATE_EMAIL_DOMAINS = {"corvane.example"}
PERSONAL_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "proton.me", "protonmail.com"}


def _ind(code: str, strength: str, detail: str, ids) -> dict:
    return {"code": code, "strength": strength, "detail": detail, "event_ids": sorted(set(int(i) for i in ids))}


def local_hour(ts: datetime, tz: timezone) -> float:
    t = ts.astimezone(tz)
    return t.hour + t.minute / 60


def compute_indicators(events: list[dict], baseline: dict, role: str, department: str, tz: timezone) -> list[dict]:
    """events: chronologically ordered dicts with id, timestamp, event_type, domain, url, filename, source,
    safe_metadata. baseline: output of analyzer.build_baseline()."""
    out: list[dict] = []
    if not events:
        return out
    exp = expected_categories(role, department)
    for e in events:
        e.setdefault("category", categorize(e.get("domain"), e.get("url")))

    downloads = [e for e in events if e["event_type"] == "download"]
    copies = [e for e in events if e["event_type"] == "file_access" and (e.get("safe_metadata") or {}).get("activity") == "copy"]

    # 1. Burst of downloads (>=3 within 10 minutes)
    for i in range(len(downloads)):
        win = [d for d in downloads[i:] if d["timestamp"] - downloads[i]["timestamp"] <= timedelta(minutes=10)]
        if len(win) >= 3:
            out.append(_ind("download_burst", "moderate",
                            f"{len(win)} downloads within 10 minutes", [d["id"] for d in win]))
            break

    # 2. Sensitive-looking download/copy followed by external file-sharing or personal email
    sensitive_moves = [e for e in downloads + copies if is_sensitive_filename(e.get("filename"))]
    sensitive_moves.sort(key=lambda e: e["timestamp"])
    shares = [e for e in events if (e["event_type"] in ("navigation", "tab_activated")
                                    and e["category"] in ("file_sharing", "personal_email"))
              or (e["event_type"] == "email" and (e.get("domain") or "") in PERSONAL_EMAIL_DOMAINS
                  and (e.get("safe_metadata") or {}).get("attachments", 0))]
    for s in sensitive_moves:
        after = [x for x in shares if timedelta(0) <= x["timestamp"] - s["timestamp"] <= timedelta(minutes=60)]
        if after:
            related = [m for m in sensitive_moves if abs((m["timestamp"] - s["timestamp"]).total_seconds()) <= 3600]
            out.append(_ind("sensitive_transfer_sequence", "strong",
                            "sensitive-looking file download/copy followed within 60 min by external file-sharing "
                            "or personal-email activity (visiting a sharing/upload page does NOT prove an upload)",
                            [m["id"] for m in related] + [x["id"] for x in after]))
            break

    # 3. External file-sharing access without such a sequence (weak, informational)
    if shares and not any(i["code"] == "sensitive_transfer_sequence" for i in out):
        nav_shares = [x for x in shares if x["event_type"] != "email"]
        if nav_shares:
            out.append(_ind("external_file_sharing_visit", "weak",
                            "visited external file-sharing / personal storage site(s): "
                            + ", ".join(sorted({x['domain'] for x in nav_shares})), [x["id"] for x in nav_shares]))

    # 4. Sensitive systems outside the role's usual scope
    off = [e for e in events if e["category"] in SENSITIVE_CATEGORIES and e["category"] not in exp]
    if off:
        cats = Counter(e["category"] for e in off)
        out.append(_ind("sensitive_system_outside_role", "moderate" if len(off) >= 2 else "weak",
                        f"access to systems not typical for role '{role}': "
                        + ", ".join(f"{c} x{n}" for c, n in cats.items()), [e["id"] for e in off]))

    # 5. Removable media combined with file copies
    usb = [e for e in events if e["event_type"] == "removable_media"
           and (e.get("safe_metadata") or {}).get("activity") == "connect"]
    for u in usb:
        near = [c for c in copies if timedelta(0) <= c["timestamp"] - u["timestamp"] <= timedelta(minutes=30)]
        if near:
            strength = "strong" if any(is_sensitive_filename(c.get("filename")) for c in near) else "moderate"
            out.append(_ind("removable_media_copy", strength,
                            f"removable media connected and {len(near)} file copy events within 30 min",
                            [u["id"]] + [c["id"] for c in near]))
            break

    # 6. Job-search activity together with data movement
    jobs = [e for e in events if e["category"] == "job_search" and "job_search" not in exp]
    if jobs and (sensitive_moves or len(downloads) >= 3):
        out.append(_ind("job_search_with_data_movement", "moderate",
                        "job-search browsing in the same window as file downloads/copies (common and usually benign "
                        "on its own)", [e["id"] for e in jobs] + [m["id"] for m in (sensitive_moves or downloads)]))

    # 7. Off-hours activity *combined* with data movement (off-hours alone is never flagged)
    ws, we = baseline.get("typical_hours_local", [9.0, 19.0])
    offh = [e for e in downloads + copies if not (ws - 1 <= local_hour(e["timestamp"], tz) <= we + 1)]
    if len(offh) >= 2:
        out.append(_ind("off_hours_data_movement", "weak",
                        f"{len(offh)} downloads/copies outside the employee's usual hours "
                        f"({ws:.0f}:00-{we:.0f}:00 local)", [e["id"] for e in offh]))

    # 8. Deviation from historical behaviour: download volume and unfamiliar domains (live events only)
    live = [e for e in events if e["source"] == "chrome_extension"]
    live_dl = [e for e in live if e["event_type"] == "download"]
    avg_dl = baseline.get("avg_downloads_per_day", 0.0)
    if len(live_dl) >= 4 and len(live_dl) > 3 * max(avg_dl, 0.5):
        out.append(_ind("download_volume_above_baseline", "moderate",
                        f"{len(live_dl)} live downloads vs historical average {avg_dl:.1f}/day",
                        [e["id"] for e in live_dl]))
    known = set(baseline.get("known_domains", []))
    if known and live:
        new = [e for e in live if e.get("domain") and e["domain"] not in known
               and e["category"] not in ("search", "news", "collaboration")]
        new_domains = sorted({e["domain"] for e in new})
        if len(new_domains) >= 4:
            out.append(_ind("unfamiliar_domains", "weak",
                            f"{len(new_domains)} domains never seen in this employee's history: "
                            + ", ".join(new_domains[:8]), [e["id"] for e in new][:15]))

    # 9. Large external email with attachments to personal mailbox
    ext = [e for e in events if e["event_type"] == "email" and (e.get("domain") or "") in PERSONAL_EMAIL_DOMAINS
           and (e.get("safe_metadata") or {}).get("attachments", 0)]
    if ext and not any(i["code"] == "sensitive_transfer_sequence" for i in out):
        out.append(_ind("attachments_to_personal_email", "moderate",
                        "email with attachments sent to a personal mailbox domain (metadata only)",
                        [e["id"] for e in ext]))
    return out
