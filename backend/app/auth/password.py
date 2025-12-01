"""
密码处理模块
使用bcrypt进行密码哈希和验证
"""
import bcrypt


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码字符串
    """
    salt = bcrypt.gensalt(rounds=12)  # 12轮，安全性和性能的平衡
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码是否正确
    
    Args:
        password: 明文密码
        hashed: 存储的哈希密码
        
    Returns:
        密码是否匹配
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False
