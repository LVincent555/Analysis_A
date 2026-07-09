# Backend Tests

This backend now uses `uv` for the default Python test workflow.

## Stable Unit Tests

Run from `backend/`:

```powershell
uv run pytest
```

The default pytest profile only collects `tests/unit`. These tests should be fast, deterministic, and independent from the real PostgreSQL service and market data files.

The unit suite also includes architecture guardrails for the DEC-002 migration:

- `contexts/*/domain` must not import FastAPI, SQLAlchemy, JWT, cache, routers, services, or ORM models.
- Every context must keep the `api / application / domain / infrastructure` layer layout.

## Full Backend Dependencies

The default dependency set is enough for core API/auth/cache tests. Data-analysis dependencies are optional:

```powershell
uv run --extra analysis pytest
```

Full application import smoke checks should also use the analysis extra because the legacy aggregate routers still import Numpy/Pandas-backed analysis services.

## API Contract Baseline

Run from `backend/`:

```powershell
uv run --extra analysis python scripts/export_api_contract.py
```

The current baseline is recorded in `app/contexts/API_CONTRACT_BASELINE.md`.

## Legacy Tests

The existing root-level files under `tests/` are legacy or integration-style tests. Several of them depend on a running backend service, real credentials, or local market data. They are intentionally not part of the default pytest collection yet.

As the backend architecture migrates, move stable cases into `tests/unit` and server/data-dependent cases into a later `tests/integration` profile.
