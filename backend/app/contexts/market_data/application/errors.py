"""Market data application errors."""

from __future__ import annotations


class MarketDataNotFoundError(Exception):
    """Raised when market data is missing for a requested query."""


class OfflineSyncDisabledError(Exception):
    """Raised when the current user cannot use offline sync."""


class InvalidOfflineSyncRequestError(Exception):
    """Raised when an offline sync request has invalid parameters."""


class DataAdminConflictError(Exception):
    """Raised when a data admin task conflicts with an active task."""


class DataAdminNotFoundError(Exception):
    """Raised when data admin resources cannot be found."""


class InvalidDataAdminRequestError(Exception):
    """Raised when a data admin request is invalid."""
