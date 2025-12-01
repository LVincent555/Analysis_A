"""
FastAPI依赖注入模块
提供认证相关的依赖函数
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from .jwt_handler import verify_token

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)

# 会话密钥缓存 (生产环境应使用Redis)
# 格式: {user_id: session_key_bytes}
_session_keys: dict[int, bytes] = {}


def set_session_key(user_id: int, session_key: bytes):
    """存储用户会话密钥"""
    _session_keys[user_id] = session_key


def get_session_key_by_user_id(user_id: int) -> Optional[bytes]:
    """获取用户会话密钥"""
    return _session_keys.get(user_id)


def remove_session_key(user_id: int):
    """移除用户会话密钥"""
    _session_keys.pop(user_id, None)


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token或Token已过期",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 检查Token类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要访问令牌，而非刷新令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
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
    user: User = Depends(get_current_user)
) -> bytes:
    """
    获取当前用户的会话密钥
    
    Args:
        user: 当前登录用户
        
    Returns:
        会话密钥字节串
        
    Raises:
        HTTPException: 会话密钥不存在时抛出401错误
    """
    session_key = get_session_key_by_user_id(user.id)
    
    if not session_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return session_key


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
