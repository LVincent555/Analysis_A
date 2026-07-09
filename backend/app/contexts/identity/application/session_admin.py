"""Admin session management use cases for the Identity context."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .commands import CleanupExpiredSessionsCommand, RevokeAdminSessionCommand, RevokeUserSessionsCommand
from .ports import IdentityAuditLogRepository, IdentitySessionRepository, IdentityUserRepository
from .queries import GetAdminSessionDetailQuery, ListAdminSessionsQuery


ACTIVE_THRESHOLD_SECONDS = 120
LOST_THRESHOLD_SECONDS = 300
IDLE_THRESHOLD_SECONDS = 1800


@dataclass(frozen=True, slots=True)
class SuccessResult:
    success: bool
    message: str
    affected: int | None = None
    session_id: int | None = None


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


def get_session_display_status(session: Any, now=None) -> dict[str, str]:
    """Calculate the admin-facing display status for a user session."""

    current_time = now or utc_now_naive()

    if getattr(session, "is_revoked", False):
        return {"status": "revoked", "color": "gray", "label": "已撤销"}

    expires_at = getattr(session, "expires_at", None)
    if expires_at and expires_at < current_time:
        return {"status": "expired", "color": "gray", "label": "已过期"}

    last_active = getattr(session, "last_active", None) or getattr(session, "created_at", None)
    if not last_active:
        return {"status": "unknown", "color": "gray", "label": "未知"}

    idle_seconds = (current_time - last_active).total_seconds()
    client_status = getattr(session, "current_status", None) or "online"

    if idle_seconds <= ACTIVE_THRESHOLD_SECONDS:
        if client_status == "locked":
            return {"status": "locked", "color": "gray", "label": "锁屏"}
        if client_status == "idle":
            return {"status": "idle", "color": "yellow", "label": "空闲"}
        return {"status": "active", "color": "green", "label": "活跃"}

    if idle_seconds <= LOST_THRESHOLD_SECONDS:
        return {"status": "lost", "color": "red", "label": "失联"}

    if idle_seconds <= IDLE_THRESHOLD_SECONDS:
        if client_status == "locked":
            return {"status": "locked", "color": "gray", "label": "锁屏"}
        return {"status": "idle", "color": "yellow", "label": "空闲"}

    return {"status": "offline", "color": "black", "label": "离线"}


def _session_list_item(session: Any, display_status: dict[str, str]) -> dict:
    user = getattr(session, "user", None)
    return {
        "id": session.id,
        "user_id": session.user_id,
        "username": getattr(user, "username", None) if user else None,
        "nickname": getattr(user, "nickname", None) if user else None,
        "device_id": session.device_id,
        "device_name": session.device_name,
        "ip_address": session.ip_address,
        "platform": session.platform,
        "app_version": session.app_version,
        "location": session.location,
        "status": display_status["status"],
        "status_color": display_status["color"],
        "status_label": display_status["label"],
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_active": session.last_active.isoformat() if session.last_active else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "is_revoked": session.is_revoked,
    }


def _session_detail(session: Any, display_status: dict[str, str]) -> dict:
    user = getattr(session, "user", None)
    return {
        "id": session.id,
        "user_id": session.user_id,
        "username": getattr(user, "username", None) if user else None,
        "nickname": getattr(user, "nickname", None) if user else None,
        "user_role": getattr(user, "role", None) if user else None,
        "device_id": session.device_id,
        "device_name": session.device_name,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "platform": session.platform,
        "app_version": session.app_version,
        "location": session.location,
        "status": display_status["status"],
        "status_color": display_status["color"],
        "status_label": display_status["label"],
        "current_status": session.current_status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "last_active": session.last_active.isoformat() if session.last_active else None,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "is_revoked": session.is_revoked,
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
        "revoked_by": session.revoked_by,
    }


class ListAdminSessionsUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository) -> None:
        self.sessions = sessions

    def execute(self, query: ListAdminSessionsQuery) -> dict:
        now = utc_now_naive()
        total, rows = self.sessions.list_for_admin(
            page=query.page,
            page_size=query.page_size,
            user_id=query.user_id,
            username=query.username,
            include_expired=query.include_expired,
            include_revoked=query.include_revoked,
            now=now,
        )

        items = []
        for session in rows:
            display_status = get_session_display_status(session, now)
            if query.status and query.status != "all" and display_status["status"] != query.status:
                continue
            items.append(_session_list_item(session, display_status))

        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "items": items,
        }


class GetAdminSessionDetailUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository) -> None:
        self.sessions = sessions

    def execute(self, query: GetAdminSessionDetailQuery) -> dict:
        session = self.sessions.get_by_id(query.session_id)
        if not session:
            raise _not_found("会话不存在")

        return _session_detail(session, get_session_display_status(session))


class GetAdminSessionStatisticsUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository) -> None:
        self.sessions = sessions

    def execute(self) -> dict:
        now = utc_now_naive()
        rows = self.sessions.list_active(now)
        status_counts = {
            "active": 0,
            "idle": 0,
            "locked": 0,
            "lost": 0,
            "offline": 0,
        }

        for session in rows:
            status_value = get_session_display_status(session, now)["status"]
            if status_value in status_counts:
                status_counts[status_value] += 1

        return {
            "total_sessions": len(rows),
            "online_users": self.sessions.count_online_users(
                now=now,
                active_since=now - timedelta(minutes=5),
            ),
            "status_distribution": status_counts,
            "platform_distribution": self.sessions.platform_distribution(now),
            "updated_at": now.isoformat(),
        }


class RevokeAdminSessionUseCase:
    def __init__(
        self,
        *,
        sessions: IdentitySessionRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.sessions = sessions
        self.audit_logs = audit_logs

    def execute(self, command: RevokeAdminSessionCommand) -> SuccessResult:
        session = self.sessions.get_by_id(command.session_id)
        if not session:
            raise _validation_error("会话不存在")

        if session.is_revoked:
            raise _validation_error("会话已被撤销")

        if session.user_id == command.operator_id:
            raise _validation_error("不能撤销自己的会话")

        now = utc_now_naive()
        session.is_revoked = True
        session.revoked_at = now
        session.revoked_by = command.operator_id

        target_user = getattr(session, "user", None)
        target_name = f"{getattr(target_user, 'username', 'unknown')}@{session.device_name or session.device_id}"
        self.audit_logs.record(
            log_type="SESSION",
            action="session_revoke",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="session",
            target_id=session.id,
            target_name=target_name,
            ip_address=command.ip_address,
            detail={
                "device_id": session.device_id,
                "device_name": session.device_name,
                "user_id": session.user_id,
            },
        )
        self.sessions.commit()

        return SuccessResult(success=True, message="会话已撤销", session_id=session.id)


class RevokeUserSessionsUseCase:
    def __init__(
        self,
        *,
        users: IdentityUserRepository,
        sessions: IdentitySessionRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.audit_logs = audit_logs

    def execute(self, command: RevokeUserSessionsCommand) -> SuccessResult:
        if command.user_id == command.operator_id and not command.exclude_current:
            raise _validation_error("不能撤销自己的所有会话")

        if command.user_id == command.operator_id and command.exclude_current and command.current_session_id is None:
            raise _validation_error("无法识别当前会话，不能排除当前会话")

        target_user = self.users.get_by_id(command.user_id)
        if not target_user:
            raise _validation_error("用户不存在")

        exclude_session_id = command.current_session_id if command.exclude_current else None
        rows = self.sessions.list_unrevoked_for_user(command.user_id, exclude_session_id)
        if not rows:
            return SuccessResult(success=True, message="没有需要撤销的会话", affected=0)

        now = utc_now_naive()
        for session in rows:
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_by = command.operator_id

        if not command.exclude_current:
            target_user.token_version = (target_user.token_version or 1) + 1

        affected = len(rows)
        self.audit_logs.record(
            log_type="SESSION",
            action="session_revoke_all",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=command.user_id,
            target_name=target_user.username,
            ip_address=command.ip_address,
            detail={
                "affected_sessions": affected,
                "exclude_current": command.exclude_current,
                "current_session_id": command.current_session_id,
            },
        )
        self.sessions.commit()

        return SuccessResult(success=True, message=f"已撤销 {affected} 个会话", affected=affected)


class CleanupExpiredSessionsUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository) -> None:
        self.sessions = sessions

    def execute(self, command: CleanupExpiredSessionsCommand) -> int:
        cutoff = utc_now_naive() - timedelta(days=command.days)
        deleted = self.sessions.cleanup_expired_before(cutoff)
        self.sessions.commit()
        return deleted
