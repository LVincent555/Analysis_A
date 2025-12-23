"""
用户管理 API 路由
v1.1.0: 提供用户CRUD、状态管理、密码管理等接口
"""
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from ..auth.dependencies import require_admin
from ..services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/users", tags=["用户管理"])


# ==================== 请求/响应模型 ====================

class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    role: str = Field("user", description="角色: admin/user")
    allowed_devices: int = Field(3, ge=1, le=10, description="允许设备数")
    offline_enabled: bool = Field(True, description="允许离线使用")
    offline_days: int = Field(7, ge=1, le=30, description="离线天数")
    expires_at: Optional[str] = Field(None, description="过期时间(ISO格式)")
    remark: Optional[str] = Field(None, description="备注")


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)
    remark: Optional[str] = None
    role: Optional[str] = Field(None, description="角色: admin/user")
    allowed_devices: Optional[int] = Field(None, ge=1, le=10)
    offline_enabled: Optional[bool] = None
    offline_days: Optional[int] = Field(None, ge=1, le=30)
    expires_at: Optional[str] = Field(None, description="过期时间(ISO格式)或null")


class ToggleStatusRequest(BaseModel):
    """切换状态请求"""
    is_active: bool


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=6, max_length=100)
    force_logout: bool = Field(True, description="是否强制登出所有设备")


class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    action: str = Field(..., description="操作类型: enable/disable/delete")
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")


class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str


# ==================== API 端点 ====================

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
    db: Session = Depends(get_db)
):
    """
    获取用户列表（分页）
    
    - **page**: 页码，从1开始
    - **page_size**: 每页数量，最大100
    - **search**: 搜索用户名/邮箱/昵称
    - **role**: 角色筛选 (admin/user)
    - **status**: 状态筛选 (active/inactive/locked/expired)
    - **sort_by**: 排序字段 (created_at/last_login/username)
    - **sort_order**: 排序方向 (asc/desc)
    """
    result = UserService.get_users(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return result


@router.get("/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    获取用户详情
    
    包含用户基本信息和活跃会话列表
    """
    result = UserService.get_user_detail(db, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")
    return result


@router.post("", response_model=SuccessResponse)
async def create_user(
    req: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    创建新用户
    
    - 用户名必须唯一
    - 密码长度至少6位
    - 默认角色为普通用户
    """
    try:
        # 处理过期时间
        expires_at = None
        if req.expires_at:
            expires_at = datetime.fromisoformat(req.expires_at.replace('Z', '+00:00'))
        
        user = UserService.create_user(
            db=db,
            username=req.username,
            password=req.password,
            operator=current_user,
            email=req.email,
            phone=req.phone,
            nickname=req.nickname,
            role=req.role,
            allowed_devices=req.allowed_devices,
            offline_enabled=req.offline_enabled,
            offline_days=req.offline_days,
            expires_at=expires_at,
            remark=req.remark
        )
        return SuccessResponse(message=f"用户 {user.username} 创建成功")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")


@router.put("/{user_id}", response_model=SuccessResponse)
async def update_user(
    user_id: int,
    req: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    更新用户信息
    
    - 只更新请求中包含的字段
    - 不能修改用户名和密码（密码使用专门的重置接口）
    """
    try:
        # 构建更新字段
        update_data = req.model_dump(exclude_unset=True)
        
        # 处理 expires_at 为 null 的情况
        if 'expires_at' in update_data:
            if update_data['expires_at'] is None or update_data['expires_at'] == 'null':
                update_data['expires_at'] = None
        
        user = UserService.update_user(
            db=db,
            user_id=user_id,
            operator=current_user,
            **update_data
        )
        return SuccessResponse(message=f"用户 {user.username} 更新成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新用户失败: {str(e)}")


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    hard: bool = Query(False, description="是否硬删除"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    删除用户
    
    - **hard=false**: 软删除，保留数据但标记为已删除
    - **hard=true**: 硬删除，彻底删除用户和所有会话
    - 不能删除自己
    """
    try:
        UserService.delete_user(
            db=db,
            user_id=user_id,
            operator=current_user,
            hard_delete=hard
        )
        return SuccessResponse(message="用户已删除")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")


@router.post("/{user_id}/toggle-status", response_model=SuccessResponse)
async def toggle_user_status(
    user_id: int,
    req: ToggleStatusRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    启用/禁用用户
    
    - 禁用用户时会自动撤销所有活跃会话
    - 不能禁用自己
    """
    try:
        user = UserService.toggle_user_status(
            db=db,
            user_id=user_id,
            operator=current_user,
            is_active=req.is_active
        )
        status_text = "启用" if req.is_active else "禁用"
        return SuccessResponse(message=f"用户 {user.username} 已{status_text}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"切换用户状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/{user_id}/reset-password", response_model=SuccessResponse)
async def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    重置用户密码
    
    - 密码长度至少6位
    - 可选择是否强制登出所有设备
    - 会自动解锁账户（如果被锁定）
    """
    try:
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        UserService.reset_password(
            db=db,
            user_id=user_id,
            operator=current_user,
            new_password=req.new_password,
            force_logout=req.force_logout
        )
        return SuccessResponse(message=f"用户 {user.username} 密码已重置")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")


@router.post("/{user_id}/unlock", response_model=SuccessResponse)
async def unlock_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    解锁用户账户
    
    - 重置登录失败计数
    - 清除锁定时间
    """
    try:
        user = UserService.unlock_user(
            db=db,
            user_id=user_id,
            operator=current_user
        )
        return SuccessResponse(message=f"用户 {user.username} 已解锁")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"解锁用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"解锁失败: {str(e)}")


@router.post("/batch", response_model=SuccessResponse)
async def batch_operation(
    req: BatchOperationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    批量操作用户
    
    - **action**: enable(启用) / disable(禁用) / delete(删除)
    - **user_ids**: 用户ID列表
    - 不会影响操作者自己的账户
    """
    if req.action not in ["enable", "disable", "delete"]:
        raise HTTPException(status_code=400, detail="无效的操作类型")
    
    try:
        affected = UserService.batch_operation(
            db=db,
            user_ids=req.user_ids,
            action=req.action,
            operator=current_user
        )
        
        action_text = {"enable": "启用", "disable": "禁用", "delete": "删除"}
        return SuccessResponse(message=f"已{action_text[req.action]} {affected} 个用户")
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")
