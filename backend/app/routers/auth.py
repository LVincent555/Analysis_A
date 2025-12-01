"""
认证路由模块
提供用户注册、登录、Token刷新等API
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User, UserSession
from ..auth.password import hash_password, verify_password
from ..auth.jwt_handler import (
    create_access_token, 
    create_refresh_token, 
    verify_token,
    ACCESS_TOKEN_EXPIRE_HOURS
)
from ..auth.dependencies import get_current_user, set_session_key, remove_session_key
from ..crypto.aes_handler import AESCrypto, generate_key, get_master_crypto

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== 请求/响应模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    device_id: str = Field(default="default", description="设备标识")
    device_name: Optional[str] = Field(default=None, description="设备名称")


class RefreshRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class LoginResponse(BaseModel):
    """登录响应"""
    token: str
    refresh_token: str
    session_key: str  # 加密的会话密钥
    expires_at: str
    user: dict


class RegisterResponse(BaseModel):
    """注册响应"""
    success: bool
    message: str
    user_id: Optional[int] = None


# ==================== API端点 ====================

@router.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - 用户名唯一性检查
    - 密码bcrypt哈希存储
    - 生成用户专属加密密钥
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == req.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 生成用户密钥
    user_key = generate_key()
    
    # 用主密钥加密用户密钥
    master_crypto = get_master_crypto()
    user_key_encrypted = master_crypto.encrypt_key(user_key)
    
    # 创建用户
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        user_key_encrypted=user_key_encrypted
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return RegisterResponse(
        success=True,
        message="注册成功",
        user_id=user.id
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - 验证用户名密码
    - 生成JWT Token和Refresh Token
    - 生成会话密钥（用于后续加密通信）
    - 返回加密的会话密钥（客户端用密码派生密钥解密）
    """
    # 查找用户
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查账户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # 检查设备数量限制
    active_sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.expires_at > datetime.utcnow()
    ).count()
    
    if active_sessions >= user.allowed_devices:
        # 删除最旧的会话
        oldest_session = db.query(UserSession).filter(
            UserSession.user_id == user.id
        ).order_by(UserSession.last_active.asc()).first()
        
        if oldest_session:
            db.delete(oldest_session)
    
    # 生成会话密钥
    session_key = generate_key()
    
    # 用密码派生密钥加密会话密钥
    from ..crypto.aes_handler import derive_key_from_password, key_to_base64
    password_derived_key = derive_key_from_password(req.password)
    password_crypto = AESCrypto(password_derived_key)
    session_key_encrypted = password_crypto.encrypt_key(session_key)
    
    # 生成Token
    token = create_access_token(user.id, req.device_id)
    refresh_token = create_refresh_token(user.id, req.device_id)
    
    # 计算过期时间
    expires_at = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    # 创建或更新会话记录
    existing_session = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.device_id == req.device_id
    ).first()
    
    if existing_session:
        existing_session.session_key_encrypted = session_key_encrypted
        existing_session.refresh_token = refresh_token
        existing_session.expires_at = expires_at
        existing_session.last_active = datetime.utcnow()
        if req.device_name:
            existing_session.device_name = req.device_name
    else:
        new_session = UserSession(
            user_id=user.id,
            device_id=req.device_id,
            device_name=req.device_name,
            session_key_encrypted=session_key_encrypted,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        db.add(new_session)
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()
    
    # 存储会话密钥到内存（用于后续请求解密）
    set_session_key(user.id, session_key)
    
    return LoginResponse(
        token=token,
        refresh_token=refresh_token,
        session_key=session_key_encrypted,
        expires_at=expires_at.isoformat(),
        user=user.to_dict()
    )


@router.post("/refresh")
async def refresh_token(
    req: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌
    
    使用Refresh Token获取新的Access Token
    """
    # 验证Refresh Token
    payload = verify_token(req.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要刷新令牌"
        )
    
    user_id = int(payload.get("sub"))
    device_id = payload.get("device", "default")
    
    # 查找用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用"
        )
    
    # 验证会话
    session = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.device_id == device_id,
        UserSession.refresh_token == req.refresh_token
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话不存在或已失效"
        )
    
    # 生成新Token
    new_token = create_access_token(user_id, device_id)
    expires_at = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    # 更新会话活跃时间
    session.last_active = datetime.utcnow()
    session.expires_at = expires_at
    db.commit()
    
    return {
        "token": new_token,
        "expires_at": expires_at.isoformat()
    }


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    用户登出
    
    清除当前设备的会话
    """
    # 从内存中移除会话密钥
    remove_session_key(user.id)
    
    # 可选：删除数据库中的会话记录
    # 这里保留会话记录，只是让Token自然过期
    
    return {"success": True, "message": "已登出"}


@router.post("/logout-all")
async def logout_all_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    登出所有设备
    
    清除用户的所有会话
    """
    # 删除所有会话
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.commit()
    
    # 从内存中移除会话密钥
    remove_session_key(user.id)
    
    return {"success": True, "message": "已登出所有设备"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改密码
    """
    # 验证旧密码
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    user.password_hash = hash_password(req.new_password)
    
    # 清除所有会话（强制重新登录）
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    
    db.commit()
    
    # 从内存中移除会话密钥
    remove_session_key(user.id)
    
    return {"success": True, "message": "密码已修改，请重新登录"}


@router.get("/me")
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return user.to_dict()


@router.get("/sessions")
async def get_user_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的所有活跃会话
    """
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    
    return {
        "sessions": [
            {
                "device_id": s.device_id,
                "device_name": s.device_name,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "last_active": s.last_active.isoformat() if s.last_active else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None
            }
            for s in sessions
        ],
        "total": len(sessions),
        "limit": user.allowed_devices
    }
