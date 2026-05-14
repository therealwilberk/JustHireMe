"""
Ingestion Pipeline Verification Script

WARNING: This is NOT a deterministic test. It requires:
  - LLM API key (calls Claude via agents.ingestor.ingest)
  - SQLite database writes (via db.client.save_settings)
  - Active LLM service

Usage: PYTHONPATH=backend python scripts/run_ingestion_pipeline.py
"""

import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingestion")

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from agents.ingestor import ingest
from db.client import save_settings

# Ensure we have a sample text to ingest
test_text = """
Vasudev Siddh
AI Engineer
Skills: Python, React, LangChain, Kuzu, LLMs
Experience: Built JustHireMe, an autonomous job seeker.
"""

try:
    log.info("Attempting ingestion…")
    result = ingest(raw=test_text)
    log.info("Ingestion result: skills=%d exp=%d projects=%d",
             len(result.skills), len(result.exp), len(result.projects))
except Exception as e:
    log.error("Ingestion failed: %s", e, exc_info=True)
    sys.exit(1)
