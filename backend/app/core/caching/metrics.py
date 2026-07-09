"""Lightweight cache operation metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    expired_cleanups: int = 0
    loader_errors: int = 0
    persister_errors: int = 0
    operation_errors: int = 0
    recoveries: int = 0
    last_error: str | None = None

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1

    def record_set(self, count: int = 1) -> None:
        self.sets += count

    def record_delete(self, count: int = 1) -> None:
        self.deletes += count

    def record_eviction(self, count: int = 1) -> None:
        self.evictions += count

    def record_expired_cleanup(self, count: int) -> None:
        self.expired_cleanups += count

    def record_loader_error(self, exc: Exception) -> None:
        self.loader_errors += 1
        self.last_error = str(exc)

    def record_persister_error(self, exc: Exception) -> None:
        self.persister_errors += 1
        self.last_error = str(exc)

    def record_operation_error(self, exc: Exception) -> None:
        self.operation_errors += 1
        self.last_error = str(exc)

    def record_recovery(self) -> None:
        self.recoveries += 1

    def to_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "expired_cleanups": self.expired_cleanups,
            "loader_errors": self.loader_errors,
            "persister_errors": self.persister_errors,
            "operation_errors": self.operation_errors,
            "recoveries": self.recoveries,
            "last_error": self.last_error,
        }
