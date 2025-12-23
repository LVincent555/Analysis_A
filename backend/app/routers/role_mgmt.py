"""
角色权限 API 路由
提供角色CRUD、权限管理等接口
v1.1.0
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from ..auth.dependencies import get_current_user
from ..services.role_service import RoleService, ALL_PERMISSIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/roles", tags=["角色管理"])


# ==================== 请求/响应模型 ====================

class RoleCreateRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=50, description="角色代码")
    display_name: str = Field(..., min_length=2, max_length=100, description="显示名称")
    description: Optional[str] = Field(None, max_length=255, description="描述")
    permissions: List[str] = Field(default=[], description="权限列表")


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    role_id: int


class PermissionsResponse(BaseModel):
    """权限列表响应"""
    permissions: dict


# ==================== 依赖项 ====================

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """验证管理员权限"""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ==================== API 端点 ====================

@router.get("/permissions", response_model=PermissionsResponse)
def get_all_permissions(admin: User = Depends(get_admin_user)):
    """获取所有权限定义"""
    return {"permissions": ALL_PERMISSIONS}


@router.get("")
def get_roles(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取角色列表"""
    try:
        roles = RoleService.get_roles(db, include_inactive)
        return {"roles": roles}
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{role_id}")
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取角色详情"""
    try:
        role = RoleService.get_role(db, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_role(
    req: RoleCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """创建角色"""
    try:
        ip_address = request.client.host if request.client else None
        result = RoleService.create_role(
            db=db,
            name=req.name,
            display_name=req.display_name,
            description=req.description,
            permissions=req.permissions,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{role_id}")
def update_role(
    role_id: int,
    req: RoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """更新角色"""
    try:
        ip_address = request.client.host if request.client else None
        result = RoleService.update_role(
            db=db,
            role_id=role_id,
            display_name=req.display_name,
            description=req.description,
            permissions=req.permissions,
            is_active=req.is_active,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """删除角色"""
    try:
        ip_address = request.client.host if request.client else None
        result = RoleService.delete_role(
            db=db,
            role_id=role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/assign")
def assign_role_to_user(
    user_id: int,
    req: AssignRoleRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """为用户分配角色"""
    try:
        ip_address = request.client.host if request.client else None
        result = RoleService.assign_role_to_user(
            db=db,
            user_id=user_id,
            role_id=req.role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分配角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}/role/{role_id}")
def remove_role_from_user(
    user_id: int,
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """移除用户的角色"""
    try:
        ip_address = request.client.host if request.client else None
        result = RoleService.remove_role_from_user(
            db=db,
            user_id=user_id,
            role_id=role_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"移除角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/permissions")
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取用户的所有权限"""
    try:
        permissions = RoleService.get_user_permissions(db, user_id)
        return {"user_id": user_id, "permissions": permissions}
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/check/{permission}")
def check_user_permission(
    user_id: int,
    permission: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """检查用户是否有指定权限"""
    try:
        has_permission = RoleService.check_permission(db, user_id, permission)
        return {
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission
        }
    except Exception as e:
        logger.error(f"检查权限失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
