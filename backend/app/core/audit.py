"""Compatibility entrypoint for Operations audit buffering."""

from ..contexts.operations.infrastructure.audit_buffer import (
    AuditLogBuffer,
    AuditLogEntry,
    audit_log,
    create_audit_sync_callback,
)

__all__ = [
    "AuditLogBuffer",
    "AuditLogEntry",
    "audit_log",
    "create_audit_sync_callback",
]
