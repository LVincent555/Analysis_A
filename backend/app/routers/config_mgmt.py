"""
系统配置 API 路由
提供配置查询、更新等接口
v1.1.0
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from ..auth.dependencies import get_current_user
from ..services.config_service import ConfigService, CONFIG_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/config", tags=["系统配置"])


# ==================== 请求/响应模型 ====================

class ConfigItem(BaseModel):
    """配置项"""
    id: int
    key: str
    value: Any
    raw_value: str
    type: str
    category: str
    category_label: str
    description: Optional[str]
    updated_at: Optional[str]


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    categories: dict
    configs: List[ConfigItem]


class ConfigUpdateRequest(BaseModel):
    """更新配置请求"""
    value: Any = Field(..., description="配置值")


class BatchUpdateRequest(BaseModel):
    """批量更新请求"""
    updates: Dict[str, Any] = Field(..., description="配置键值对")


class PasswordPolicyResponse(BaseModel):
    """密码策略响应"""
    min_length: int
    max_length: int
    require_digit: bool
    require_upper: bool
    require_lower: bool
    require_special: bool
    expire_days: int


class LoginPolicyResponse(BaseModel):
    """登录策略响应"""
    max_attempts: int
    lockout_minutes: int
    attempt_reset_minutes: int
    captcha_enabled: bool
    captcha_threshold: int


class SessionPolicyResponse(BaseModel):
    """会话策略响应"""
    access_token_hours: int
    refresh_token_days: int
    max_devices: int
    idle_timeout_minutes: int
    single_device: bool


class ValidatePasswordRequest(BaseModel):
    """验证密码请求"""
    password: str


class ValidatePasswordResponse(BaseModel):
    """验证密码响应"""
    valid: bool
    errors: List[str]


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

@router.get("/categories")
def get_categories(admin: User = Depends(get_admin_user)):
    """获取配置分类列表"""
    return {"categories": CONFIG_CATEGORIES}


@router.get("", response_model=ConfigListResponse)
def get_all_configs(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    获取所有配置
    
    - **category**: 可选，按分类筛选 (password/login/session/system)
    """
    try:
        configs = ConfigService.get_all(db, category)
        return {
            "categories": CONFIG_CATEGORIES,
            "configs": configs
        }
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-category")
def get_configs_by_category(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """按分类获取配置"""
    try:
        return {
            "categories": CONFIG_CATEGORIES,
            "configs": ConfigService.get_by_category(db)
        }
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/password", response_model=PasswordPolicyResponse)
def get_password_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取密码策略"""
    return ConfigService.get_password_policy(db)


@router.get("/policy/login", response_model=LoginPolicyResponse)
def get_login_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取登录策略"""
    return ConfigService.get_login_policy(db)


@router.get("/policy/session", response_model=SessionPolicyResponse)
def get_session_policy(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取会话策略"""
    return ConfigService.get_session_policy(db)


@router.put("/{key}")
def update_config(
    key: str,
    req: ConfigUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """更新单个配置"""
    try:
        ip_address = request.client.host if request.client else None
        result = ConfigService.update(
            db=db,
            key=key,
            value=req.value,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
def batch_update_configs(
    req: BatchUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """批量更新配置"""
    try:
        ip_address = request.client.host if request.client else None
        result = ConfigService.batch_update(
            db=db,
            updates=req.updates,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except Exception as e:
        logger.error(f"批量更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{key}/reset")
def reset_config(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """重置配置为默认值"""
    try:
        ip_address = request.client.host if request.client else None
        result = ConfigService.reset_to_default(
            db=db,
            key=key,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address=ip_address
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-password", response_model=ValidatePasswordResponse)
def validate_password(
    req: ValidatePasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """验证密码是否符合策略"""
    return ConfigService.validate_password(db, req.password)
