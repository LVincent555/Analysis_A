# Composition Root Baseline

`backend/app/main.py` is the current composition root.

Current responsibilities:

- Creates the FastAPI app.
- Configures logging, CORS, gzip and authentication middleware.
- Registers legacy routers.
- Initializes cache regions.
- Runs startup checks.
- Preloads configuration and Numpy-backed analysis cache.
- Starts and stops the cache database syncer.
- Mounts the optional Electron update directory.

Migration rule:

- `main.py` may wire adapters, routers, middleware and lifecycle hooks.
- `main.py` must not grow new business rules.
- Context routers should be registered from `contexts/*/api` after each context migration.
- Startup work should move into small composition functions or infrastructure adapters before old services are retired.

Initial router ownership:

| Router source | Target context | Notes |
|------|------|------|
| `routers/auth.py` | Identity | Keep `/api/auth/*` compatible during migration. |
| `routers/user_mgmt.py` | Identity | Admin-facing user management. |
| `routers/session_mgmt.py` | Identity | Admin-facing session management. |
| `routers/role_mgmt.py` | Identity | Roles and permissions. |
| `routers/cache_mgmt.py` | Operations | Cache management command surface. |
| `routers/config_mgmt.py` | Operations | System config and policy surfaces. |
| `routers/log_mgmt.py` | Operations | Operation log query/export surface. |
| `routers/admin.py` | Operations + MarketData | Split upload/import/delete orchestration from operations. |
| `routers/stock.py`, `routers/sector.py` | MarketData | Read-side data access. |
| `routers/analysis.py`, `routers/industry*.py`, `routers/rank_jump.py`, `routers/steady_rise.py`, `routers/strategies.py` | Analysis | CQRS query side first. |
| `routers/board_heat.py`, `routers/ext_board_mgmt.py` | BoardHeat | Sync/calculation commands and heat queries. |
| `routers/secure.py` | Platform + Identity | Encryption gateway depends on identity session keys. |
