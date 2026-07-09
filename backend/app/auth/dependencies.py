"""Compatibility FastAPI dependencies for identity."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from ..contexts.identity.application.use_cases import AuthenticateAccessTokenUseCase
from ..contexts.identity.infrastructure.jwt_tokens import jwt_token_issuer
from ..contexts.identity.infrastructure.repositories import (
    SqlAlchemyIdentitySessionRepository,
    SqlAlchemyIdentityUserRepository,
)
from ..contexts.identity.infrastructure.session_key_store import session_key_store
from ..shared.errors import AppError, ErrorCode
from ..shared.time import utc_now_naive

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


# ==================== 会话密钥管理 (使用统一缓存系统) ====================

def _session_key_cache_key(user_id: int, device_id: str = "default") -> str:
    return f"{user_id}:{device_id or 'default'}"


def set_session_key(user_id: int, session_key: bytes, device_id: str = "default"):
    """
    存储用户会话密钥
    
    v0.6.0: 使用统一缓存系统
    v2.2.2: 改为独立 session_keys 分区，并按 user_id:device_id 存储
    """
    session_key_store.set(user_id, session_key, device_id)


def get_session_key_by_user_id(user_id: int, device_id: str = "default") -> Optional[bytes]:
    """
    获取用户会话密钥
    
    v0.6.0: 优先从统一缓存系统读取
    v2.2.2: 按 user_id:device_id 读取，避免多设备互相覆盖
    """
    return session_key_store.get(user_id, device_id)


def remove_session_key(user_id: int, device_id: Optional[str] = None):
    """
    移除用户会话密钥
    
    v0.6.0: 同时清理缓存和降级存储
    v2.2.2: 支持按设备清理；device_id=None 时清理该用户所有设备
    """
    session_key_store.remove(user_id, device_id)


# 降级存储 (缓存系统未初始化时使用)
_fallback_session_keys = session_key_store.fallback


def _raise_unauthorized(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def _identity_http_error(error: AppError) -> HTTPException:
    status_code = status.HTTP_401_UNAUTHORIZED
    if error.code == ErrorCode.FORBIDDEN:
        status_code = status.HTTP_403_FORBIDDEN

    return HTTPException(
        status_code=status_code,
        detail=error.message,
        headers={"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None,
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户
    
    从Authorization头中提取JWT Token，验证并返回用户对象
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        当前登录的User对象
        
    Raises:
        HTTPException: Token无效或用户不存在时抛出401错误
    """
    if not credentials:
        _raise_unauthorized("未提供认证凭证")
    
    token = credentials.credentials
    use_case = AuthenticateAccessTokenUseCase(
        token_issuer=jwt_token_issuer,
        users=SqlAlchemyIdentityUserRepository(db),
        sessions=SqlAlchemyIdentitySessionRepository(db),
    )
    try:
        result = use_case.execute(token)
    except AppError as error:
        raise _identity_http_error(error) from error

    user = result.user
    user._auth_payload = result.payload
    user._auth_session = result.session
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    可选的用户认证
    
    如果提供了有效Token则返回用户，否则返回None
    用于既支持登录用户又支持匿名访问的接口
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_session_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bytes:
    """
    获取当前用户的会话密钥
    
    如果内存中没有，尝试从数据库恢复（处理后端重启场景）
    
    Args:
        user: 当前登录用户
        db: 数据库会话
        
    Returns:
        会话密钥字节串
        
    Raises:
        HTTPException: 会话密钥不存在时抛出401错误
    """
    payload = getattr(user, "_auth_payload", {}) or {}
    device_id = payload.get("device", "default")
    session_key = get_session_key_by_user_id(user.id, device_id)
    
    if not session_key:
        # 尝试从数据库恢复会话密钥（处理后端重启的情况）
        session_key = await restore_session_key_from_db(user.id, db, device_id)
        
    if not session_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return session_key


async def restore_session_key_from_db(
    user_id: int,
    db: Session,
    device_id: str = "default"
) -> Optional[bytes]:
    """
    从数据库恢复用户会话密钥到内存
    
    当后端重启后，内存中的会话密钥丢失，需要从数据库恢复
    """
    sessions = SqlAlchemyIdentitySessionRepository(db)
    session = sessions.find_active_session(user_id, device_id, utc_now_naive())
    
    if not session or not session.session_key_encrypted:
        return None
    
    try:
        # 注意：session_key_encrypted 是用密码派生密钥加密的，无法直接解密
        # 这里返回 None，让用户重新登录
        # 如果想要支持自动恢复，需要改为用主密钥加密会话密钥
        return None
    except Exception as e:
        print(f"恢复会话密钥失败: {e}")
        return None


async def require_admin(
    user: User = Depends(get_current_user)
) -> User:
    """
    要求管理员权限
    
    Args:
        user: 当前登录用户
        
    Returns:
        管理员用户对象
        
    Raises:
        HTTPException: 非管理员时抛出403错误
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user
