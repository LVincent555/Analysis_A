"""Admin role and permission management routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ....auth.dependencies import get_current_user
from .schemas import PermissionsResponse
from ..application.commands import (
    AssignRoleToUserCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    RemoveRoleFromUserCommand,
    UpdateRoleCommand,
)
from ..application.queries import (
    CheckUserPermissionQuery,
    GetRoleDetailQuery,
    GetUserPermissionsQuery,
    ListRolesQuery,
)
from ..application.rbac_queries import (
    CheckUserPermissionUseCase,
    GetPermissionsCatalogUseCase,
    GetRoleDetailUseCase,
    GetUserPermissionsUseCase,
    ListRolesUseCase,
)
from ..application.rbac_commands import (
    AssignRoleToUserUseCase,
    CreateRoleUseCase,
    DeleteRoleUseCase,
    RemoveRoleFromUserUseCase,
    UpdateRoleUseCase,
)
from ..infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentityRoleQueryRepository,
)
from ....database import get_db
from ....db_models import User
from ....shared.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/roles", tags=["角色管理"])


class RoleCreateRequest(BaseModel):
    """Create role request."""

    name: str = Field(..., min_length=2, max_length=50, description="角色代码")
    display_name: str = Field(..., min_length=2, max_length=100, description="显示名称")
    description: Optional[str] = Field(None, max_length=255, description="描述")
    permissions: list[str] = Field(default=[], description="权限列表")


class RoleUpdateRequest(BaseModel):
    """Update role request."""

    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None


class AssignRoleRequest(BaseModel):
    """Assign role request."""

    role_id: int


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


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _role_query_repository(db: Session) -> SqlAlchemyIdentityRoleQueryRepository:
    return SqlAlchemyIdentityRoleQueryRepository(db)


def _role_components(db: Session):
    return (
        SqlAlchemyIdentityRoleQueryRepository(db),
        SqlAlchemyIdentityAuditLogRepository(db),
    )


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Verify administrator permission."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


@router.get("/permissions", response_model=PermissionsResponse)
def get_all_permissions(admin: User = Depends(get_admin_user)):
    """Get all permission definitions."""

    return GetPermissionsCatalogUseCase().execute()


@router.get("")
def get_roles(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get role list."""

    try:
        return ListRolesUseCase(
            roles=_role_query_repository(db),
        ).execute(ListRolesQuery(include_inactive=include_inactive))
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to list roles: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{role_id}")
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get role detail."""

    try:
        return GetRoleDetailUseCase(
            roles=_role_query_repository(db),
        ).execute(GetRoleDetailQuery(role_id=role_id))
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get role detail: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("")
def create_role(
    req: RoleCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Create role."""

    roles, audit_logs = _role_components(db)
    try:
        result = CreateRoleUseCase(
            roles=roles,
            audit_logs=audit_logs,
        ).execute(CreateRoleCommand(
            name=req.name,
            display_name=req.display_name,
            description=req.description,
            permissions=req.permissions,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=_client_ip(request),
        ))
        return {
            "success": result.success,
            "message": result.message,
            "role_id": result.role_id,
        }
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to create role: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{role_id}")
def update_role(
    role_id: int,
    req: RoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Update role."""

    roles, audit_logs = _role_components(db)
    try:
        result = UpdateRoleUseCase(
            roles=roles,
            audit_logs=audit_logs,
        ).execute(UpdateRoleCommand(
            role_id=role_id,
            display_name=req.display_name,
            description=req.description,
            permissions=req.permissions,
            is_active=req.is_active,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=_client_ip(request),
        ))
        return {"success": result.success, "message": result.message}
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to update role: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Delete role."""

    roles, audit_logs = _role_components(db)
    try:
        result = DeleteRoleUseCase(
            roles=roles,
            audit_logs=audit_logs,
        ).execute(DeleteRoleCommand(
            role_id=role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=_client_ip(request),
        ))
        return {"success": result.success, "message": result.message}
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to delete role: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/user/{user_id}/assign")
def assign_role_to_user(
    user_id: int,
    req: AssignRoleRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Assign a role to a user."""

    roles, audit_logs = _role_components(db)
    try:
        result = AssignRoleToUserUseCase(
            roles=roles,
            audit_logs=audit_logs,
        ).execute(AssignRoleToUserCommand(
            user_id=user_id,
            role_id=req.role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=_client_ip(request),
        ))
        return {"success": result.success, "message": result.message}
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to assign role: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/user/{user_id}/role/{role_id}")
def remove_role_from_user(
    user_id: int,
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Remove a role from a user."""

    roles, audit_logs = _role_components(db)
    try:
        result = RemoveRoleFromUserUseCase(
            roles=roles,
            audit_logs=audit_logs,
        ).execute(RemoveRoleFromUserCommand(
            user_id=user_id,
            role_id=role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=_client_ip(request),
        ))
        return {"success": result.success, "message": result.message}
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to remove role: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/user/{user_id}/permissions")
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Get permissions granted to a user."""

    try:
        permissions = GetUserPermissionsUseCase(
            roles=_role_query_repository(db),
        ).execute(GetUserPermissionsQuery(user_id=user_id))
        return {"user_id": user_id, "permissions": permissions}
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get user permissions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/user/{user_id}/check/{permission}")
def check_user_permission(
    user_id: int,
    permission: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """Check if a user has a permission."""

    try:
        has_permission = CheckUserPermissionUseCase(
            roles=_role_query_repository(db),
        ).execute(CheckUserPermissionQuery(user_id=user_id, permission=permission))
        return {
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission,
        }
    except AppError as error:
        raise _identity_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to check permission: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
