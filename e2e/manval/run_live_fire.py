"""
Live Fire End-to-End Verification Script

WARNING: This is NOT a deterministic test. It requires live services:
  - LLM API keys (Anthropic, OpenAI, etc.)
  - Headed Chromium browser (Playwright)
  - SQLite database writes
  - Real network calls to job boards

Usage: uv run python e2e/manval/run_live_fire.py [JOB_URL] [--submit]

JOB_URL  : Target application form (default: Lever public demo)
--submit : Actually click Submit (omit for dry-run)

Examples:
  uv run python e2e/manval/run_live_fire.py
  uv run python e2e/manval/run_live_fire.py https://jobs.lever.co/leverdemo/abc123 --submit
"""

import hashlib
import logging
import os
import sqlite3
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("live_fire")

_DEFAULT_URL = (
    "https://boards.greenhouse.io/embed/job_app"
    "?for=greenhouse&token=4027514002"
)

_RESUME = """
Vasudev Siddh
Software Engineer | Hyderabad, India
vasudev82090@gmail.com | +91-9000000000 | linkedin.com/in/vasudevsiddh

Summary
Full-stack engineer with 4 years of experience building production Python and TypeScript
applications. Specialised in FastAPI microservices, React dashboards, and LLM integrations.

Experience
Senior Software Engineer — Acme Corp (2022–Present)
  Led migration of monolith to FastAPI + LangGraph event-driven pipeline processing 50k req/day.
  Built React (TypeScript) real-time dashboard using WebSockets and Framer Motion.
  Skills used: Python, FastAPI, LangGraph, React, TypeScript, PostgreSQL, Docker.

Software Engineer — Beta Systems (2020–2022)
  Developed REST APIs in Python/Django serving 2M monthly active users.
  Integrated OpenAI and Anthropic APIs for document summarisation product.
  Skills used: Python, Django, Redis, PostgreSQL, OpenAI API.

Projects
JustHireMe — Autonomous job-seeking engine
  Tauri 2.0 + React/TS shell wrapping Python FastAPI sidecar. LangGraph orchestration,
  Kuzu graph DB, LanceDB vector store, Playwright browser automation.
  Stack: Python, Rust, TypeScript, React, FastAPI, LangGraph, Playwright.
  Impact: Fully autonomous pipeline from scouting to submission.

Skills
Python, TypeScript, React, FastAPI, LangGraph, Playwright, Docker, PostgreSQL,
SQLite, REST APIs, WebSockets, Anthropic Claude, LLM integrations, Kuzu, LanceDB,
Tauri, Rust (basic), Git, CI/CD.
"""

_IDENTITY = {
    "name":        "Vasudev Siddh",
    "first_name":  "Vasudev",
    "last_name":   "Siddh",
    "email":       "vasudev82090@gmail.com",
    "phone":       "+919000000000",
    "linkedin_url": "https://linkedin.com/in/vasudevsiddh",
    "website":     "https://github.com/vasudevsiddh",
    "github":      "https://github.com/vasudevsiddh",
}


def _h(u: str) -> str:
    return hashlib.md5(u.encode()).hexdigest()[:16]


def step(n: int, label: str):
    border = "=" * 60
    log.info("\n%s\n  STEP %d: %s\n%s", border, n, label, border)


def _audit_trail(jid: str):
    from db.client import sql
    c = sqlite3.connect(sql)
    rows = c.execute(
        "SELECT ts, action FROM events WHERE job_id=? ORDER BY ts", (jid,)
    ).fetchall()
    lead = c.execute(
        "SELECT title, company, status FROM leads WHERE job_id=?", (jid,)
    ).fetchone()
    c.close()
    line = "\u2550" * 60
    log.info("\n%s\n  AUDIT TRAIL\n%s", line, line)
    if lead:
        log.info("  Lead   : %s @ %s", lead[0], lead[1])
        log.info("  Status : %s", lead[2])
    for ts, action in rows:
        log.info("  %s  %s", ts, action)
    log.info("%s\n", line)


def main():
    url      = _DEFAULT_URL
    dry_run  = True
    for arg in sys.argv[1:]:
        if arg == "--submit":
            dry_run = False
        elif arg.startswith("http"):
            url = arg

    mode = "dry-run" if dry_run else "LIVE (will submit)"
    border = "=" * 60
    log.info("\n%s\n  JustHireMe Live Fire Test\n  URL  : %s\n  Mode : %s\n%s",
             border, url, mode, border)

    jid = _h(url)

    step(1, "Ingest candidate profile into graph DB")
    from agents.ingestor import run as ingest
    log.info("Calling Claude to extract profile from resume text\u2026")
    profile = ingest(raw=_RESUME)
    log.info("Ingested: %s | skills=%s exp=%s projects=%s",
             profile.n, len(profile.skills), len(profile.exp), len(profile.projects))

    step(2, "Insert sandbox lead into SQLite")
    from db.client import sql, save_lead, url_exists
    if url_exists(jid):
        log.info("Lead %s already exists \u2014 reusing", jid)
    else:
        save_lead(jid, "Software Engineer (Live Fire Demo)", "Demo Corp", url, "greenhouse")
        log.info("Inserted lead %s", jid)

    step(3, "Evaluate lead (GraphRAG scoring)")
    from agents.evaluator import score as ev_score
    from db.client import update_lead_score
    skills = [sk.n for sk in profile.skills]
    log.info("Scoring against %d skills\u2026", len(skills))
    result = ev_score(
        f"Software Engineer at Demo Corp \u2014 {url}",
        skills,
    )
    log.info("Score: %s/100", result["score"])
    log.info("Reason: %s\u2026", result["reason"][:120])
    for mp in result["match_points"]:
        log.info("  \u2713 %s", mp)

    if result["score"] < 85:
        log.info("Score < 85: forcing status to 'tailoring' for test continuity")
    update_lead_score(jid, max(result["score"], 85), result["reason"])

    step(4, "Generate tailored PDF asset")
    from agents.generator import run as gen
    lead_data = {
        "job_id":       jid,
        "title":        "Software Engineer (Live Fire Demo)",
        "company":      "Demo Corp",
        "url":          url,
        "platform":     "greenhouse",
        "skills":       skills,
        "match_points": result["match_points"],
        **_IDENTITY,
    }
    log.info("Calling Claude to draft tailored resume + cover letter\u2026")
    asset_path = gen(lead_data)
    log.info("PDF saved: %s", asset_path)

    from db.client import save_asset_path
    save_asset_path(jid, asset_path)

    step(5, f"Actuator \u2014 {'dry-run' if dry_run else 'LIVE SUBMIT'}")
    log.info("Launching headed Chromium (500ms delay between fields)\u2026")
    from agents.actuator import run as act
    job_data = {**lead_data, **_IDENTITY}
    ok = act(job_data, asset_path, dry_run=dry_run)

    if dry_run:
        log.info("Dry run complete \u2014 submit button highlighted in red, browser held open 4s")
        log.info("Fields filled: %s", ok)
    else:
        if ok:
            from db.client import mark_applied
            mark_applied(jid)
            log.info("Application SUBMITTED")
        else:
            log.warning("Submit button not found \u2014 application NOT submitted")

    step(6, "Audit trail")
    _audit_trail(jid)

    assert os.path.exists(asset_path), f"PDF not found at {asset_path}"
    log.info("PDF exists on disk")

    c = sqlite3.connect(sql)
    ev = c.execute("SELECT COUNT(*) FROM events WHERE job_id=?", (jid,)).fetchone()[0]
    c.close()
    assert ev >= 2, f"Expected >=2 events, got {ev}"
    log.info("%d events in audit log", ev)

    log.info("Live Fire verification PASSED")


if __name__ == "__main__":
    main()
