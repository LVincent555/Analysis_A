"""Write-behind audit log buffer for Operations."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from ....db_models import OperationLog

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AuditLogEntry:
    operator_id: int
    action: str
    target_name: str = ""
    detail: str = ""
    ip_address: str = ""
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AuditLogBuffer:
    def __init__(self, max_size: int = 1000) -> None:
        self._buffer: list[AuditLogEntry] = []
        self._lock = threading.Lock()
        self.max_size = max_size

    def log(
        self,
        user_id: int,
        action: str,
        target: str = "",
        detail: str = "",
        ip: str = "",
    ) -> None:
        entry = AuditLogEntry(
            operator_id=user_id,
            action=action,
            target_name=target,
            detail=detail,
            ip_address=ip,
        )

        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) > self.max_size:
                self._buffer.pop(0)

    def flush(self) -> list[AuditLogEntry]:
        with self._lock:
            entries = self._buffer.copy()
            self._buffer.clear()
            return entries

    def stats(self) -> dict:
        with self._lock:
            return {
                "pending": len(self._buffer),
                "max_size": self.max_size,
            }

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)


def _log_type_for_action(action: str) -> str:
    if action in {"login", "logout"}:
        return "LOGIN"
    if "password" in action:
        return "SECURITY"
    if "session" in action or "force_logout" in action:
        return "SESSION"
    return "SYSTEM"


def create_audit_sync_callback(
    audit_buffer: AuditLogBuffer,
    session_factory: Callable | None = None,
):
    """Create a DatabaseSyncer callback for flushing audit logs."""

    def sync_audit_logs() -> None:
        entries = audit_buffer.flush()
        if not entries:
            return

        try:
            if session_factory is None:
                from ....database import SessionLocal

                db_factory = SessionLocal
            else:
                db_factory = session_factory

            db = db_factory()
            try:
                for entry in entries:
                    db.add(
                        OperationLog(
                            log_type=_log_type_for_action(entry.action),
                            action=entry.action,
                            operator_id=entry.operator_id,
                            operator_name=None,
                            target_type="legacy_audit" if entry.target_name else None,
                            target_name=entry.target_name or None,
                            ip_address=entry.ip_address or None,
                            detail=entry.detail or None,
                            status="success",
                            created_at=entry.created_at,
                        )
                    )
                db.commit()
                logger.info("[AuditLog] Flushed %s entries", len(entries))
            except Exception as exc:
                db.rollback()
                logger.error("[AuditLog] DB error: %s", exc)
            finally:
                db.close()
        except ImportError:
            logger.warning("[AuditLog] Database module not available")

    return sync_audit_logs


audit_log = AuditLogBuffer()
