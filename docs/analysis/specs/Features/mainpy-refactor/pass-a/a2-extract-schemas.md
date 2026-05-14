# Pass A2 — Extract Pydantic Schemas

**Lines affected:** 84-169, 1623-1684, 1948
**Target file:** `backend/schemas/requests.py`
**Mode:** AFK

---

## Goal

Move all Pydantic request models out of `main.py` into `schemas/requests.py`. Pure copy — zero field changes, zero behavioral differences.

---

## What Moves

| Item | Lines in main.py |
|------|-----------------|
| `LeadStatus` type alias | 84-88 |
| `StrictBody` (base model) | 91-92 |
| `StatusBody` | 95-96 |
| `FeedbackBody` | 99-105 |
| `FollowupBody` | 108-109 |
| `ManualLeadBody` | 112-115 |
| `HelpMessage` | 118-120 |
| `HelpChatBody` | 123-125 |
| `TemplateBody` | 128-129 |
| `CandidateBody` | 132-134 |
| `SkillBody` | 137-140 |
| `ExperienceBody` | 143-148 |
| `ProjectBody` | 151-156 |
| `SettingsBody` | 159-169 |
| `GithubIngestBody` | 1623-1626 |
| `PortfolioIngestBody` | 1629-1634 |
| `ProfileSkill` | 1637-1639 |
| `ProfileExperience` | 1642-1646 |
| `ProfileProject` | 1649-1653 |
| `ProfileEntry` | 1656-1657 |
| `ProfileIdentity` | 1660-1666 |
| `ProfileCandidate` | 1669-1671 |
| `ProfileImportBody` | 1674-1684 |
| `FormReadBody` | 1948-1949 |

---

## What Changes During the Move

| Change | Reason |
|--------|--------|
| Add `from pydantic import BaseModel, ConfigDict, Field, model_validator` to top of `requests.py` | Required by models |
| Remove these imports from `main.py` | No longer defined there |
| Add `from schemas.requests import (...)` to `main.py` | Import all models at top of file |

**No field changes. No class renames. No behavior changes.**

---

## Target File Structure (`schemas/requests.py`)

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

LeadStatus = Literal["discovered", ...]

class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

class StatusBody(StrictBody):
    status: LeadStatus

# ... all other models ...
```

---

## Verification

```bash
# 1. Compile check
python -m py_compile backend/main.py
python -m py_compile backend/schemas/requests.py

# 2. Run full test suite
cd backend && uv run python -m pytest tests/ -q --tb=line
```

Both must pass. No test should fail — no behavior changed.

---

## Commit

```
refactor(a1): extract Pydantic schemas to schemas/requests.py
```
