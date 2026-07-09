"""System configuration management routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....auth.dependencies import require_admin
from ....database import get_db
from ....db_models import User
from ....shared.errors import AppError, ErrorCode
from ..application.commands import (
    BatchUpdateSystemConfigsCommand,
    ResetSystemConfigCommand,
    UpdateSystemConfigCommand,
)
from ..application.config_commands import (
    BatchUpdateSystemConfigsUseCase,
    ResetSystemConfigUseCase,
    UpdateSystemConfigUseCase,
)
from ..application.config_queries import (
    GetConfigCategoriesUseCase,
    GetLoginPolicyUseCase,
    GetPasswordPolicyUseCase,
    GetSessionPolicyUseCase,
    GroupSystemConfigsByCategoryUseCase,
    ListSystemConfigsUseCase,
    ValidatePasswordPolicyUseCase,
)
from ..application.queries import ListSystemConfigsQuery, ValidatePasswordPolicyQuery
from ..infrastructure.config_cache import UnifiedConfigCacheReloader
from ..infrastructure.repositories import SqlAlchemyOperationLogRepository, SqlAlchemySystemConfigRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/config", tags=["系统配置"])


class ConfigItem(BaseModel):
    id: int
    key: str
    value: Any
    raw_value: str
    type: str
    category: str
    category_label: str
    description: str | None
    updated_at: str | None


class ConfigListResponse(BaseModel):
    categories: dict
    configs: list[ConfigItem]


class ConfigUpdateRequest(BaseModel):
    value: Any = Field(..., description="配置值")


class BatchUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(..., description="配置键值对")


class PasswordPolicyResponse(BaseModel):
    min_length: int
    max_length: int
    require_digit: bool
    require_upper: bool
    require_lower: bool
    require_special: bool
    expire_days: int


class LoginPolicyResponse(BaseModel):
    max_attempts: int
    lockout_minutes: int
    attempt_reset_minutes: int
    captcha_enabled: bool
    captcha_threshold: int


class SessionPolicyResponse(BaseModel):
    access_token_hours: int
    refresh_token_days: int
    max_devices: int
    idle_timeout_minutes: int
    single_device: bool


class ValidatePasswordRequest(BaseModel):
    password: str


class ValidatePasswordResponse(BaseModel):
    valid: bool
    errors: list[str]


def _operations_http_error(error: AppError) -> HTTPException:
    status_map = {
        ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
        ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
        ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INFRASTRUCTURE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return HTTPException(
        status_code=status_map.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail=error.message,
    )


def _config_repository(db: Session) -> SqlAlchemySystemConfigRepository:
    return SqlAlchemySystemConfigRepository(db)


def _audit_repository(db: Session) -> SqlAlchemyOperationLogRepository:
    return SqlAlchemyOperationLogRepository(db)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _config_command_components(db: Session):
    return (
        _config_repository(db),
        _audit_repository(db),
        UnifiedConfigCacheReloader(db),
    )


@router.get("/categories")
def get_categories(admin: User = Depends(require_admin)):
    """Get config categories."""

    return GetConfigCategoriesUseCase().execute()


@router.get("", response_model=ConfigListResponse)
def get_all_configs(
    category: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get all configs, optionally filtered by category."""

    try:
        return {
            "categories": GetConfigCategoriesUseCase().execute()["categories"],
            "configs": ListSystemConfigsUseCase(configs=_config_repository(db)).execute(
                ListSystemConfigsQuery(category=category)
            ),
        }
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to list system configs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/by-category")
def get_configs_by_category(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get configs grouped by category."""

    try:
        return {
            "categories": GetConfigCategoriesUseCase().execute()["categories"],
            "configs": GroupSystemConfigsByCategoryUseCase(configs=_config_repository(db)).execute(),
        }
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to group system configs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/policy/password", response_model=PasswordPolicyResponse)
def get_password_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get password policy."""

    return GetPasswordPolicyUseCase(configs=_config_repository(db)).execute()


@router.get("/policy/login", response_model=LoginPolicyResponse)
def get_login_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get login policy."""

    return GetLoginPolicyUseCase(configs=_config_repository(db)).execute()


@router.get("/policy/session", response_model=SessionPolicyResponse)
def get_session_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get session policy."""

    return GetSessionPolicyUseCase(configs=_config_repository(db)).execute()


@router.put("/{key}")
def update_config(
    key: str,
    req: ConfigUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update one config."""

    configs, audit_logs, config_cache = _config_command_components(db)
    try:
        return UpdateSystemConfigUseCase(
            configs=configs,
            audit_logs=audit_logs,
            config_cache=config_cache,
        ).execute(
            UpdateSystemConfigCommand(
                key=key,
                value=req.value,
                operator_id=admin.id,
                operator_name=admin.username,
                ip_address=_client_ip(request),
            )
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to update system config: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("")
def batch_update_configs(
    req: BatchUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Batch update configs."""

    configs, audit_logs, config_cache = _config_command_components(db)
    try:
        return BatchUpdateSystemConfigsUseCase(
            configs=configs,
            audit_logs=audit_logs,
            config_cache=config_cache,
        ).execute(
            BatchUpdateSystemConfigsCommand(
                updates=req.updates,
                operator_id=admin.id,
                operator_name=admin.username,
                ip_address=_client_ip(request),
            )
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to batch update system configs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{key}/reset")
def reset_config(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Reset one config to its default value."""

    configs, audit_logs, config_cache = _config_command_components(db)
    try:
        return ResetSystemConfigUseCase(
            configs=configs,
            audit_logs=audit_logs,
            config_cache=config_cache,
        ).execute(
            ResetSystemConfigCommand(
                key=key,
                operator_id=admin.id,
                operator_name=admin.username,
                ip_address=_client_ip(request),
            )
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to reset system config: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/validate-password", response_model=ValidatePasswordResponse)
def validate_password(
    req: ValidatePasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Validate password by current password policy."""

    return ValidatePasswordPolicyUseCase(configs=_config_repository(db)).execute(
        ValidatePasswordPolicyQuery(password=req.password)
    )
