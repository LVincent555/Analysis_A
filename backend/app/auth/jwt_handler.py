"""
JWT Token处理模块
提供Token的生成和验证功能
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError

# 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production-32chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    user_id: int, 
    device_id: str = "default",
    expires_hours: int = ACCESS_TOKEN_EXPIRE_HOURS
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
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = {
        "sub": str(user_id),
        "device": device_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    device_id: str = "default",
    expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS
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
    expire = datetime.utcnow() + timedelta(days=expires_days)
    payload = {
        "sub": str(user_id),
        "device": device_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """
    验证Token并返回payload
    
    Args:
        token: JWT Token字符串
        
    Returns:
        解码后的payload字典，验证失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        print(f"JWT验证失败: {e}")
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    获取Token的过期时间
    
    Args:
        token: JWT Token字符串
        
    Returns:
        过期时间，无效Token返回None
    """
    payload = verify_token(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None
