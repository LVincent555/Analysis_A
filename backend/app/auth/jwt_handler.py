"""Compatibility entrypoint for JWT token handling."""

from datetime import datetime
from typing import Optional

from ..contexts.identity.infrastructure.jwt_tokens import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    jwt_token_issuer,
)


def create_access_token(
    user_id: int, 
    device_id: str = "default",
    expires_hours: int = ACCESS_TOKEN_EXPIRE_HOURS,
    token_version: Optional[int] = None
) -> str:
    """
    创建访问令牌
    
    Args:
        user_id: 用户ID
        device_id: 设备标识
        expires_hours: 过期时间（小时）
        
    Returns:
        JWT Token字符串
    """
    return jwt_token_issuer.create_access_token(
        user_id=user_id,
        device_id=device_id,
        expires_hours=expires_hours,
        token_version=token_version,
    )


def create_refresh_token(
    user_id: int,
    device_id: str = "default",
    expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
    token_version: Optional[int] = None
) -> str:
    """
    创建刷新令牌
    
    Args:
        user_id: 用户ID
        device_id: 设备标识
        expires_days: 过期时间（天）
        
    Returns:
        JWT Refresh Token字符串
    """
    return jwt_token_issuer.create_refresh_token(
        user_id=user_id,
        device_id=device_id,
        expires_days=expires_days,
        token_version=token_version,
    )


def verify_token(token: str) -> Optional[dict]:
    """
    验证Token并返回payload
    
    Args:
        token: JWT Token字符串
        
    Returns:
        解码后的payload字典，验证失败返回None
    """
    return jwt_token_issuer.verify_token(token)


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    获取Token的过期时间
    
    Args:
        token: JWT Token字符串
        
    Returns:
        过期时间，无效Token返回None
    """
    return jwt_token_issuer.get_token_expiry(token)
