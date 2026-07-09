"""Board heat application errors."""

from __future__ import annotations


class BoardHeatDataNotFoundError(Exception):
    """Raised when board heat data is missing for a requested query."""
