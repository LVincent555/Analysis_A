# ORM Ownership Baseline

`backend/app/db_models.py` remains the temporary ORM aggregate. Physical model splitting is deferred until repository adapters and import compatibility are stable.

| ORM object | Table | Target owner | Migration note |
|------|------|------|------|
| `Stock` | `stocks` | MarketData | Basic stock metadata. |
| `DailyStockData` | `daily_stock_data` | MarketData | Daily stock facts; Analysis reads through query repositories. |
| `Sector` | `sectors` | MarketData | Basic sector metadata. |
| `SectorDailyData` | `daily_sector_data` | MarketData | Daily sector facts; Analysis reads through query repositories. |
| `User` | `users` | Identity | Keep legacy ORM until Identity repositories are in place. |
| `UserSession` | `user_sessions` | Identity | Session lifecycle and device tracking. |
| `Role` | `roles` | Identity | Role and permission metadata. |
| `user_roles` | `user_roles` | Identity | Role membership association table. |
| `SystemConfig` | `system_configs` | Operations | Config and policy source of truth. |
| `OperationLog` | `operation_logs` | Operations | Operation/audit read model. |

Rules:

- Do not move ORM classes one at a time without preserving `Base.metadata`.
- Do not make SQLAlchemy ORM models act as pure domain entities.
- New context code should depend on repository/query ports before directly importing `db_models.py`.
- A later Level should introduce context infrastructure modules that re-export ORM models or repository adapters, then retire this aggregate.
