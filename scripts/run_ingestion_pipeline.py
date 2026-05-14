"""
Ingestion Pipeline Verification Script

WARNING: This is NOT a deterministic test. It requires:
  - LLM API key (calls Claude via agents.ingestor.ingest)
  - SQLite database writes (via db.client.save_settings)
  - Active LLM service

Usage: PYTHONPATH=backend python scripts/run_ingestion_pipeline.py
"""

import sys
import os

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
    print("Attempting ingestion...")
    result = ingest(raw=test_text)
    print(f"Ingestion successful! Found {len(result.skills)} skills.")
except Exception as e:
    import traceback
    print(f"Ingestion failed with error: {e}")
    traceback.print_exc()
