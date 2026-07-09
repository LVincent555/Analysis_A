# Backend Contexts

This package is the new home for backend business modules.

Dependency direction:

```text
api -> application -> domain
infrastructure -> application ports + domain
domain -> stdlib + app.shared only
```

Rules:

- Keep FastAPI code in `api`.
- Keep use-case orchestration in `application`.
- Keep business invariants in `domain`.
- Keep SQLAlchemy, JWT, cache, files, Akshare, Pandas and Numpy in `infrastructure`.
- Legacy `routers/`, `services/` and `auth/` may remain as compatibility shells during migration.
