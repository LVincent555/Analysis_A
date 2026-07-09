# Identity Context

Owns users, authentication, authorization, roles, permissions, sessions and tokens.

Initial migration policy:

- Preserve existing `/api/auth/*`, user, role and session management routes.
- Move password hashing, JWT issuing, session key storage and session policy first.
- Keep SQLAlchemy models in the legacy `db_models.py` until ORM ownership is settled.
