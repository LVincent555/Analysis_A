# API Contract Baseline

Generated command:

```powershell
cd backend
uv run --extra analysis python scripts/export_api_contract.py
```

Baseline date: 2026-07-08

Current route count: 124

Contract rule:

- During DEC-002 migration, preserve paths, methods, status behavior and JSON field names unless a later DEC explicitly approves a breaking change.
- Default `uv run pytest` does not import the full analysis stack. Use `uv run --extra analysis` for full app route contract export.
- The route list is exported by `backend/scripts/export_api_contract.py`; update this baseline after each migration Level and record the RES.
