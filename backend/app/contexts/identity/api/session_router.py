"""
Admin session management routes.

This legacy router is now an HTTP adapter for the Identity context.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ....auth.dependencies import get_current_user
from .schemas import (
    RevokeUserSessionsRequest,
    SessionListResponse,
    SessionStatisticsResponse,
    SuccessResponse,
)
from ..application.commands import (
    CleanupExpiredSessionsCommand,
    RevokeAdminSessionCommand,
    RevokeUserSessionsCommand,
)
from ..application.queries import GetAdminSessionDetailQuery, ListAdminSessionsQuery
from ..application.session_admin import (
    CleanupExpiredSessionsUseCase,
    GetAdminSessionDetailUseCase,
    GetAdminSessionStatisticsUseCase,
    ListAdminSessionsUseCase,
    RevokeAdminSessionUseCase,
    RevokeUserSessionsUseCase,
)
from ..infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentitySessionRepository,
    SqlAlchemyIdentityUserRepository,
)
from ....database import get_db
from ....db_models import User
from ....shared.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sessions", tags=["会话管理"])


def _identity_http_error(error: AppError) -> HTTPException:
    status_map = {
        ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
        ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
        ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(
        status_code=status_map.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail=error.message,
    )


def _identity_components(db: Session):
    return (
        SqlAlchemyIdentityUserRepository(db),
        SqlAlchemyIdentitySessionRepository(db),
        SqlAlchemyIdentityAuditLogRepository(db),
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _current_session_id(user: User) -> int | None:
    session = getattr(user, "_auth_session", None)
    if not session:
        return None
    return getattr(session, "id", None)


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify administrator permission."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


@router.get("", response_model=SessionListResponse)
def get_sessions(
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    session_status: Optional[str] = None,
    include_expired: bool = False,
    include_revoked: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get admin session list."""

    _, sessions, _ = _identity_components(db)
    use_case = ListAdminSessionsUseCase(sessions=sessions)
    try:
        return use_case.execute(
            ListAdminSessionsQuery(
                page=page,
                page_size=page_size,
                user_id=user_id,
                username=username,
                status=session_status,
                include_expired=include_expired,
                include_revoked=include_revoked,
            )
        )
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/statistics", response_model=SessionStatisticsResponse)
def get_session_statistics(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get admin session statistics."""

    _, sessions, _ = _identity_components(db)
    try:
        return GetAdminSessionStatisticsUseCase(sessions=sessions).execute()
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get session statistics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}")
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get session detail."""

    _, sessions, _ = _identity_components(db)
    try:
        return GetAdminSessionDetailUseCase(sessions=sessions).execute(
            GetAdminSessionDetailQuery(session_id=session_id)
        )
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get session detail: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/revoke", response_model=SuccessResponse)
def revoke_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Revoke a single session."""

    _, sessions, audit_logs = _identity_components(db)
    use_case = RevokeAdminSessionUseCase(
        sessions=sessions,
        audit_logs=audit_logs,
    )
    try:
        result = use_case.execute(
            RevokeAdminSessionCommand(
                session_id=session_id,
                operator_id=admin.id,
                operator_name=admin.username,
                ip_address=_client_ip(request),
            )
        )
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to revoke session: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "success": result.success,
        "message": result.message,
        "session_id": result.session_id,
    }


@router.post("/user/{user_id}/revoke-all", response_model=SuccessResponse)
def revoke_user_all_sessions(
    user_id: int,
    req: RevokeUserSessionsRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Revoke all sessions owned by a user."""

    users, sessions, audit_logs = _identity_components(db)
    use_case = RevokeUserSessionsUseCase(
        users=users,
        sessions=sessions,
        audit_logs=audit_logs,
    )
    try:
        result = use_case.execute(
            RevokeUserSessionsCommand(
                user_id=user_id,
                operator_id=admin.id,
                operator_name=admin.username,
                ip_address=_client_ip(request),
                exclude_current=req.exclude_current,
                current_session_id=_current_session_id(admin) if req.exclude_current else None,
            )
        )
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to revoke user sessions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "success": result.success,
        "message": result.message,
        "affected": result.affected,
    }


@router.post("/cleanup")
def cleanup_expired_sessions(
    days: int = 30,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Cleanup expired sessions."""

    _, sessions, _ = _identity_components(db)
    try:
        deleted = CleanupExpiredSessionsUseCase(sessions=sessions).execute(
            CleanupExpiredSessionsCommand(days=days)
        )
        return {
            "success": True,
            "message": f"已清理 {deleted} 个过期会话",
            "deleted": deleted,
        }
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to cleanup sessions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
