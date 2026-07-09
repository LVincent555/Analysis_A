"""Admin user management routes."""

from datetime import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....auth.dependencies import require_admin
from ..application.commands import (
    BatchAdminUsersCommand,
    CreateAdminUserCommand,
    DeleteAdminUserCommand,
    ResetAdminUserPasswordCommand,
    ToggleAdminUserStatusCommand,
    UnlockAdminUserCommand,
    UpdateAdminUserCommand,
)
from ..application.queries import GetAdminUserDetailQuery, ListAdminUsersQuery
from ..application.user_commands import (
    BatchAdminUsersUseCase,
    CreateAdminUserUseCase,
    DeleteAdminUserUseCase,
    ResetAdminUserPasswordUseCase,
    ToggleAdminUserStatusUseCase,
    UnlockAdminUserUseCase,
    UpdateAdminUserUseCase,
)
from ..application.user_queries import GetAdminUserDetailUseCase, ListAdminUsersUseCase
from ..infrastructure.crypto_provider import identity_crypto_provider
from ..infrastructure.password_hasher import password_hasher
from ..infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentityUserCommandRepository,
    SqlAlchemyIdentityUserQueryRepository,
)
from ....database import get_db
from ....db_models import User
from ....shared.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/users", tags=["用户管理"])


class UserCreateRequest(BaseModel):
    """Create user request."""

    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    role: str = Field("user", description="角色: super_admin/admin/user/readonly")
    allowed_devices: int = Field(3, ge=1, le=10, description="允许设备数")
    offline_enabled: bool = Field(True, description="允许离线使用")
    offline_days: int = Field(7, ge=1, le=30, description="离线天数")
    expires_at: Optional[str] = Field(None, description="过期时间(ISO格式)")
    remark: Optional[str] = Field(None, description="备注")


class UserUpdateRequest(BaseModel):
    """Update user request."""

    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)
    remark: Optional[str] = None
    role: Optional[str] = Field(None, description="角色: super_admin/admin/user/readonly")
    allowed_devices: Optional[int] = Field(None, ge=1, le=10)
    offline_enabled: Optional[bool] = None
    offline_days: Optional[int] = Field(None, ge=1, le=30)
    expires_at: Optional[str] = Field(None, description="过期时间(ISO格式)或null")


class ToggleStatusRequest(BaseModel):
    """Toggle user status request."""

    is_active: bool


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    new_password: str = Field(..., min_length=6, max_length=100)
    force_logout: bool = Field(True, description="是否强制登出所有设备")


class BatchOperationRequest(BaseModel):
    """Batch operation request."""

    action: str = Field(..., description="操作类型: enable/disable/delete")
    user_ids: list[int] = Field(..., min_items=1, description="用户ID列表")


class SuccessResponse(BaseModel):
    """Success response."""

    success: bool = True
    message: str


def _identity_http_error(error: AppError) -> HTTPException:
    status_map = {
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.VALIDATION_ERROR: 400,
    }
    return HTTPException(status_code=status_map.get(error.code, 500), detail=error.message)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value or value == "null":
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _query_repository(db: Session) -> SqlAlchemyIdentityUserQueryRepository:
    return SqlAlchemyIdentityUserQueryRepository(db)


def _command_components(db: Session):
    return (
        SqlAlchemyIdentityUserCommandRepository(db),
        SqlAlchemyIdentityAuditLogRepository(db),
    )


@router.get("")
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    status: Optional[str] = Query(None, description="状态筛选: active/inactive/locked/expired"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get paginated user list."""

    try:
        return ListAdminUsersUseCase(
            users=_query_repository(db),
        ).execute(ListAdminUsersQuery(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        ))
    except AppError as error:
        raise _identity_http_error(error) from error


@router.get("/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get user detail."""

    try:
        return GetAdminUserDetailUseCase(
            users=_query_repository(db),
        ).execute(GetAdminUserDetailQuery(user_id=user_id))
    except AppError as error:
        raise _identity_http_error(error) from error


@router.post("", response_model=SuccessResponse)
async def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user."""

    users, audit_logs = _command_components(db)
    use_case = CreateAdminUserUseCase(
        users=users,
        audit_logs=audit_logs,
        password_hasher=password_hasher,
        crypto=identity_crypto_provider,
    )
    try:
        result = use_case.execute(CreateAdminUserCommand(
            username=req.username,
            password=req.password,
            operator_id=current_user.id,
            operator_name=current_user.username,
            email=req.email,
            phone=req.phone,
            nickname=req.nickname,
            role=req.role,
            allowed_devices=req.allowed_devices,
            offline_enabled=req.offline_enabled,
            offline_days=req.offline_days,
            expires_at=_parse_optional_datetime(req.expires_at),
            remark=req.remark,
        ))
        return SuccessResponse(message=f"用户 {result.user.username} 创建成功")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to create user: %s", exc)
        raise HTTPException(status_code=500, detail=f"创建用户失败: {exc}") from exc


@router.put("/{user_id}", response_model=SuccessResponse)
async def update_user(
    user_id: int,
    req: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user information."""

    update_data = req.model_dump(exclude_unset=True)
    if update_data.get("expires_at") == "null":
        update_data["expires_at"] = None

    users, audit_logs = _command_components(db)
    try:
        result = UpdateAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
            UpdateAdminUserCommand(
                user_id=user_id,
                operator_id=current_user.id,
                operator_name=current_user.username,
                updates=update_data,
            )
        )
        return SuccessResponse(message=f"用户 {result.user.username} 更新成功")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to update user: %s", exc)
        raise HTTPException(status_code=500, detail=f"更新用户失败: {exc}") from exc


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    hard: bool = Query(False, description="是否硬删除"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user."""

    users, audit_logs = _command_components(db)
    try:
        DeleteAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
            DeleteAdminUserCommand(
                user_id=user_id,
                operator_id=current_user.id,
                operator_name=current_user.username,
                hard_delete=hard,
            )
        )
        return SuccessResponse(message="用户已删除")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to delete user: %s", exc)
        raise HTTPException(status_code=500, detail=f"删除用户失败: {exc}") from exc


@router.post("/{user_id}/toggle-status", response_model=SuccessResponse)
async def toggle_user_status(
    user_id: int,
    req: ToggleStatusRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enable or disable a user."""

    users, audit_logs = _command_components(db)
    try:
        result = ToggleAdminUserStatusUseCase(users=users, audit_logs=audit_logs).execute(
            ToggleAdminUserStatusCommand(
                user_id=user_id,
                operator_id=current_user.id,
                operator_name=current_user.username,
                is_active=req.is_active,
            )
        )
        status_text = "启用" if req.is_active else "禁用"
        return SuccessResponse(message=f"用户 {result.user.username} 已{status_text}")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to toggle user status: %s", exc)
        raise HTTPException(status_code=500, detail=f"操作失败: {exc}") from exc


@router.post("/{user_id}/reset-password", response_model=SuccessResponse)
async def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reset user password."""

    users, audit_logs = _command_components(db)
    try:
        result = ResetAdminUserPasswordUseCase(
            users=users,
            audit_logs=audit_logs,
            password_hasher=password_hasher,
        ).execute(ResetAdminUserPasswordCommand(
            user_id=user_id,
            operator_id=current_user.id,
            operator_name=current_user.username,
            new_password=req.new_password,
            force_logout=req.force_logout,
        ))
        return SuccessResponse(message=f"用户 {result.user.username} 密码已重置")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to reset password: %s", exc)
        raise HTTPException(status_code=500, detail=f"重置密码失败: {exc}") from exc


@router.post("/{user_id}/unlock", response_model=SuccessResponse)
async def unlock_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unlock user account."""

    users, audit_logs = _command_components(db)
    try:
        result = UnlockAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
            UnlockAdminUserCommand(
                user_id=user_id,
                operator_id=current_user.id,
                operator_name=current_user.username,
            )
        )
        return SuccessResponse(message=f"用户 {result.user.username} 已解锁")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to unlock user: %s", exc)
        raise HTTPException(status_code=500, detail=f"解锁失败: {exc}") from exc


@router.post("/batch", response_model=SuccessResponse)
async def batch_operation(
    req: BatchOperationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Batch operate users."""

    users, audit_logs = _command_components(db)
    try:
        result = BatchAdminUsersUseCase(users=users, audit_logs=audit_logs).execute(
            BatchAdminUsersCommand(
                user_ids=req.user_ids,
                action=req.action,
                operator_id=current_user.id,
                operator_name=current_user.username,
            )
        )
        action_text = {"enable": "启用", "disable": "禁用", "delete": "删除"}
        return SuccessResponse(message=f"已{action_text[req.action]} {result.affected} 个用户")
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to batch operate users: %s", exc)
        raise HTTPException(status_code=500, detail=f"批量操作失败: {exc}") from exc
