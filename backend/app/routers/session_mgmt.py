"""
会话管理 API 路由
提供会话列表、状态监控、强制下线等接口
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
from ..services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/sessions", tags=["会话管理"])


# ==================== 请求/响应模型 ====================

class SessionListResponse(BaseModel):
    """会话列表响应"""
    total: int
    page: int
    page_size: int
    items: List[dict]


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    id: int
    user_id: int
    username: Optional[str]
    nickname: Optional[str]
    user_role: Optional[str]
    device_id: str
    device_name: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    platform: Optional[str]
    app_version: Optional[str]
    location: Optional[str]
    status: str
    status_color: str
    status_label: str
    current_status: Optional[str]
    created_at: Optional[str]
    last_active: Optional[str]
    expires_at: Optional[str]
    is_revoked: bool
    revoked_at: Optional[str]
    revoked_by: Optional[int]


class RevokeSessionRequest(BaseModel):
    """撤销会话请求"""
    pass  # 无需额外参数


class RevokeUserSessionsRequest(BaseModel):
    """撤销用户所有会话请求"""
    exclude_current: bool = Field(default=False, description="是否排除当前会话")


class SessionStatisticsResponse(BaseModel):
    """会话统计响应"""
    total_sessions: int
    online_users: int
    status_distribution: dict
    platform_distribution: dict
    updated_at: str


class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool
    message: str


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
    admin: User = Depends(get_admin_user)
):
    """
    获取会话列表
    
    - **session_status**: active/idle/locked/lost/offline/all
    """
    try:
        result = SessionService.get_sessions(
            db=db,
            page=page,
            page_size=page_size,
            user_id=user_id,
            username=username,
            status=session_status,
            include_expired=include_expired,
            include_revoked=include_revoked
        )
        return result
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=SessionStatisticsResponse)
def get_session_statistics(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取会话统计信息"""
    try:
        return SessionService.get_session_statistics(db)
    except Exception as e:
        logger.error(f"获取会话统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取会话详情"""
    try:
        result = SessionService.get_session_detail(db, session_id)
        if not result:
            raise HTTPException(status_code=404, detail="会话不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/revoke", response_model=SuccessResponse)
def revoke_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    撤销（强制下线）指定会话
    
    被撤销的会话对应的客户端在下次请求时会收到 401 错误并被强制登出
    """
    try:
        # 获取客户端IP
        ip_address = request.client.host if request.client else None
        
        result = SessionService.revoke_session(
            db=db,
            session_id=session_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"撤销会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/revoke-all", response_model=SuccessResponse)
def revoke_user_all_sessions(
    user_id: int,
    req: RevokeUserSessionsRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    撤销指定用户的所有会话
    
    - **exclude_current**: 如果操作者是目标用户，可以排除当前会话
    """
    try:
        ip_address = request.client.host if request.client else None
        
        # 获取当前会话ID（如果需要排除）
        current_session_id = None
        if req.exclude_current:
            # 从请求头或其他地方获取当前会话ID
            # 这里简化处理，实际可能需要从 token 中解析
            pass
        
        result = SessionService.revoke_user_all_sessions(
            db=db,
            user_id=user_id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address,
            exclude_current=req.exclude_current,
            current_session_id=current_session_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"撤销用户会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
def cleanup_expired_sessions(
    days: int = 30,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    清理过期会话
    
    删除超过指定天数的过期或已撤销会话
    """
    try:
        deleted = SessionService.cleanup_expired_sessions(db, days)
        return {
            "success": True,
            "message": f"已清理 {deleted} 个过期会话",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"清理会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
