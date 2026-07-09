# Operations Context

Owns system configuration, cache management, audit, operation logs and backend operations.

Admin data import/delete commands are cross-context orchestration and should call Market Data or Analysis application ports instead of directly owning their data.
