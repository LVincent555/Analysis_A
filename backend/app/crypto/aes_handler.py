"""
AES-256-GCM 加解密处理模块
提供安全的对称加密功能
"""
import os
import base64
import json
import hashlib
from typing import Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 主密钥（从环境变量读取，用于加密用户密钥）
_MASTER_KEY_ENV = os.getenv("MASTER_ENCRYPTION_KEY")
_master_crypto = None

# PBKDF2参数（必须与前端一致）
PBKDF2_SALT = b'stock-analysis-salt'
PBKDF2_ITERATIONS = 10000


def derive_key_from_password(password: str) -> bytes:
    """
    从密码派生32字节密钥（与前端一致）
    
    Args:
        password: 用户密码
        
    Returns:
        32字节密钥
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=PBKDF2_SALT,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


def generate_key() -> bytes:
    """
    生成32字节随机密钥（AES-256）
    
    Returns:
        32字节的随机密钥
    """
    return os.urandom(32)


def key_to_base64(key: bytes) -> str:
    """
    将密钥转换为Base64字符串（用于存储或传输）
    
    Args:
        key: 密钥字节串
        
    Returns:
        Base64编码的字符串
    """
    return base64.b64encode(key).decode('utf-8')


def base64_to_key(key_base64: str) -> bytes:
    """
    将Base64字符串转换为密钥
    
    Args:
        key_base64: Base64编码的密钥字符串
        
    Returns:
        密钥字节串
    """
    return base64.b64decode(key_base64)


class AESCrypto:
    """
    AES-256-GCM 加解密类
    
    特点：
    - 使用AES-256算法（32字节密钥）
    - GCM模式提供认证加密（防篡改）
    - 每次加密使用随机nonce
    """
    
    def __init__(self, key: bytes):
        """
        初始化加密器
        
        Args:
            key: 32字节密钥
            
        Raises:
            ValueError: 密钥长度不是32字节时抛出
        """
        if len(key) != 32:
            raise ValueError(f"密钥必须是32字节，当前: {len(key)}字节")
        self.gcm = AESGCM(key)
        self._key = key
    
    def encrypt(self, data: Union[dict, str]) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的数据（字典或字符串）
            
        Returns:
            Base64编码的加密字符串（包含nonce）
        """
        # 转换为JSON字符串
        if isinstance(data, dict):
            plaintext = json.dumps(data, ensure_ascii=False)
        else:
            plaintext = str(data)
        
        # 生成随机nonce（GCM推荐12字节）
        nonce = os.urandom(12)
        
        # 加密
        ciphertext = self.gcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # nonce + ciphertext 合并后Base64编码
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt(self, encrypted: str) -> Union[dict, str]:
        """
        解密数据
        
        Args:
            encrypted: Base64编码的加密字符串
            
        Returns:
            解密后的数据（如果是JSON则返回字典，否则返回字符串）
            
        Raises:
            ValueError: 解密失败时抛出
        """
        try:
            # Base64解码
            raw = base64.b64decode(encrypted)
            
            # 分离nonce和密文
            nonce = raw[:12]
            ciphertext = raw[12:]
            
            # 解密
            plaintext = self.gcm.decrypt(nonce, ciphertext, None)
            text = plaintext.decode('utf-8')
            
            # 尝试解析为JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
                
        except Exception as e:
            raise ValueError(f"解密失败: {e}")
    
    def encrypt_key(self, key_to_encrypt: bytes) -> str:
        """
        加密另一个密钥（用于存储用户密钥）
        
        Args:
            key_to_encrypt: 要加密的密钥
            
        Returns:
            Base64编码的加密密钥
        """
        return self.encrypt({"key": key_to_base64(key_to_encrypt)})
    
    def decrypt_key(self, encrypted_key: str) -> bytes:
        """
        解密密钥
        
        Args:
            encrypted_key: 加密的密钥字符串
            
        Returns:
            解密后的密钥字节串
        """
        data = self.decrypt(encrypted_key)
        if isinstance(data, dict) and "key" in data:
            return base64_to_key(data["key"])
        raise ValueError("无效的加密密钥格式")


def get_master_crypto() -> AESCrypto:
    """
    获取主密钥加密器（单例）
    
    用于加密/解密用户密钥
    
    Returns:
        使用主密钥初始化的AESCrypto实例
    """
    global _master_crypto
    
    if _master_crypto is None:
        if _MASTER_KEY_ENV:
            master_key = base64_to_key(_MASTER_KEY_ENV)
        else:
            # 开发环境：使用固定密钥（生产环境必须设置环境变量）
            print("⚠️  警告: 未设置MASTER_ENCRYPTION_KEY环境变量，使用默认密钥（仅限开发）")
            master_key = b'dev-master-key-32bytes-long!!!!!'  # 正好32字节
        
        _master_crypto = AESCrypto(master_key)
    
    return _master_crypto


# 便捷函数
def encrypt_with_master(data: Union[dict, str]) -> str:
    """使用主密钥加密数据"""
    return get_master_crypto().encrypt(data)


def decrypt_with_master(encrypted: str) -> Union[dict, str]:
    """使用主密钥解密数据"""
    return get_master_crypto().decrypt(encrypted)
