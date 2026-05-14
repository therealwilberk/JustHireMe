# Pass A1 — Scaffold Directory Structure

**Lines affected:** none (new files only)
**Mode:** AFK

---

## Goal

Create the empty directory tree and `__init__.py` files for all target modules. No logic moved yet — just folders so subsequent phases can import from their new locations without `ModuleNotFoundError`.

---

## Files to Create

```
backend/
├── core/
│   └── __init__.py
├── routes/
│   └── __init__.py
├── services/
│   └── __init__.py
└── schemas/
    └── __init__.py
```

---

## Verification

```bash
python -m py_compile backend/main.py
```

Must pass. Since no imports reference these new directories yet, this is purely structural.

---

## Commit

```
chore: scaffold core/ routes/ services/ schemas/ directories
```
