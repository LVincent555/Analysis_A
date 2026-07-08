"""
FastAPI依赖注入模块
提供认证相关的依赖函数

v0.6.0: 会话密钥存储迁移到统一缓存系统
"""
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User, UserSession
from .jwt_handler import verify_token

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


# ==================== 会话密钥管理 (使用统一缓存系统) ====================

def _get_session_key_store():
    """获取加密会话密钥缓存存储"""
    try:
        from ..core.caching.manager import UnifiedCache
        if UnifiedCache.has_region("session_keys"):
            return UnifiedCache.get_region("session_keys")
    except ImportError:
        pass
    return None


def _session_key_cache_key(user_id: int, device_id: str = "default") -> str:
    return f"{user_id}:{device_id or 'default'}"


def set_session_key(user_id: int, session_key: bytes, device_id: str = "default"):
    """
    存储用户会话密钥
    
    v0.6.0: 使用统一缓存系统
    v2.2.2: 改为独立 session_keys 分区，并按 user_id:device_id 存储
    """
    cache_key = _session_key_cache_key(user_id, device_id)
    store = _get_session_key_store()
    if store:
        store.set(cache_key, {"session_key": session_key})
    else:
        # 降级: 使用模块级变量 (兼容旧版本)
        _fallback_session_keys[(user_id, device_id or "default")] = session_key


def get_session_key_by_user_id(user_id: int, device_id: str = "default") -> Optional[bytes]:
    """
    获取用户会话密钥
    
    v0.6.0: 优先从统一缓存系统读取
    v2.2.2: 按 user_id:device_id 读取，避免多设备互相覆盖
    """
    cache_key = _session_key_cache_key(user_id, device_id)
    store = _get_session_key_store()
    if store:
        data = store.get(cache_key)
        if data and isinstance(data, dict):
            return data.get("session_key")
    
    # 降级: 从模块级变量读取
    return _fallback_session_keys.get((user_id, device_id or "default"))


def remove_session_key(user_id: int, device_id: Optional[str] = None):
    """
    移除用户会话密钥
    
    v0.6.0: 同时清理缓存和降级存储
    v2.2.2: 支持按设备清理；device_id=None 时清理该用户所有设备
    """
    store = _get_session_key_store()
    if store:
        if device_id is not None:
            store.delete(_session_key_cache_key(user_id, device_id))
        elif hasattr(store, "keys"):
            prefix = f"{user_id}:"
            for key in list(store.keys()):
                if key.startswith(prefix):
                    store.delete(key)
    
    # 同时清理降级存储
    if device_id is not None:
        _fallback_session_keys.pop((user_id, device_id or "default"), None)
    else:
        for key in list(_fallback_session_keys.keys()):
            if key[0] == user_id:
                _fallback_session_keys.pop(key, None)


# 降级存储 (缓存系统未初始化时使用)
_fallback_session_keys: dict[tuple[int, str], bytes] = {}


def _raise_unauthorized(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def _get_payload_user_id(payload: dict) -> int:
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        _raise_unauthorized("无效的Token主体")


def _ensure_user_can_authenticate(user: User, payload: dict) -> None:
    now = datetime.utcnow()

    if user.deleted_at:
        _raise_unauthorized("用户不存在")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    if user.expires_at and user.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已过期"
        )

    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已锁定"
        )

    token_version = payload.get("ver")
    if token_version is not None:
        try:
            payload_token_version = int(token_version)
        except (TypeError, ValueError):
            _raise_unauthorized("无效的登录状态")

        if payload_token_version != (user.token_version or 1):
            _raise_unauthorized("登录状态已失效，请重新登录")


def _get_active_user_session(db: Session, user_id: int, device_id: str) -> Optional[UserSession]:
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.device_id == (device_id or "default"),
        UserSession.is_revoked == False,
        UserSession.expires_at > datetime.utcnow()
    ).first()


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
    payload = verify_token(token)
    
    if not payload:
        _raise_unauthorized("无效的Token或Token已过期")
    
    # 检查Token类型
    if payload.get("type") != "access":
        _raise_unauthorized("需要访问令牌，而非刷新令牌")
    
    user_id = _get_payload_user_id(payload)
    device_id = payload.get("device", "default")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        _raise_unauthorized("用户不存在")

    _ensure_user_can_authenticate(user, payload)

    session = _get_active_user_session(db, user_id, device_id)
    if not session:
        _raise_unauthorized("会话不存在或已失效")

    user._auth_payload = payload
    user._auth_session = session
    
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
    from datetime import datetime
    
    # 查找用户最近的有效会话
    session = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.device_id == (device_id or "default"),
        UserSession.is_revoked == False,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(UserSession.last_active.desc()).first()
    
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
