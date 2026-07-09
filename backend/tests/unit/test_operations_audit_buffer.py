from __future__ import annotations

from app.contexts.operations.infrastructure.audit_buffer import (
    AuditLogBuffer,
    create_audit_sync_callback,
)
from app.db_models import OperationLog


def test_audit_buffer_drops_oldest_when_full() -> None:
    buffer = AuditLogBuffer(max_size=2)

    buffer.log(1, "login")
    buffer.log(2, "logout")
    buffer.log(3, "password_change")

    entries = buffer.flush()

    assert [entry.operator_id for entry in entries] == [2, 3]
    assert buffer.size() == 0


def test_audit_sync_callback_writes_new_operation_log_fields(db_session) -> None:
    buffer = AuditLogBuffer()
    buffer.log(1, "login", target="desktop", detail='{"device":"desktop"}', ip="127.0.0.1")

    create_audit_sync_callback(buffer, session_factory=lambda: db_session)()

    log = db_session.query(OperationLog).one()
    assert log.log_type == "LOGIN"
    assert log.action == "login"
    assert log.operator_id == 1
    assert log.target_type == "legacy_audit"
    assert log.target_name == "desktop"
    assert log.detail == '{"device":"desktop"}'
    assert log.ip_address == "127.0.0.1"
    assert log.status == "success"
    assert buffer.size() == 0
