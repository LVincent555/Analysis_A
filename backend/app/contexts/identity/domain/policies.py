"""Identity domain policies."""

from datetime import datetime


def account_status(
    *,
    is_active: bool,
    deleted_at: datetime | None = None,
    locked_until: datetime | None = None,
    expires_at: datetime | None = None,
    now: datetime,
) -> str:
    if deleted_at:
        return "deleted"
    if not is_active:
        return "inactive"
    if locked_until and locked_until > now:
        return "locked"
    if expires_at and expires_at < now:
        return "expired"
    return "active"
