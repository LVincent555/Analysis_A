"""
加密模块
提供AES-256-GCM加解密功能
"""
from .aes_handler import (
    AESCrypto,
    generate_key,
    key_to_base64,
    base64_to_key,
    get_master_crypto,
    derive_key_from_password
)

__all__ = [
    'AESCrypto',
    'generate_key',
    'key_to_base64',
    'base64_to_key',
    'get_master_crypto',
    'derive_key_from_password'
]
