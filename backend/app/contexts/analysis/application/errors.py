"""Analysis application errors."""

from __future__ import annotations


class AnalysisDataNotFoundError(Exception):
    """Raised when analysis data is missing for a requested query."""
