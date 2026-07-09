"""Compatibility entrypoint for password hashing."""

from ..contexts.identity.infrastructure.password_hasher import password_hasher


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码字符串
    """
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码是否正确
    
    Args:
        password: 明文密码
        hashed: 存储的哈希密码
        
    Returns:
        密码是否匹配
    """
    return password_hasher.verify(password, hashed)
