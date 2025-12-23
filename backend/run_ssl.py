#!/usr/bin/env python3
"""
幽灵协议 - HTTPS 启动脚本
使用自签名证书启动 FastAPI 服务

使用方法:
  1. 确保 certs/ 目录下有 server.key 和 server.crt
  2. 设置环境变量: ENABLE_HTTPS=true
  3. 运行: python run_ssl.py
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

# 证书路径
CERT_DIR = Path(__file__).parent / "certs"
SSL_KEYFILE = CERT_DIR / "server.key"
SSL_CERTFILE = CERT_DIR / "server.crt"

# 配置
ENABLE_HTTPS = os.getenv("ENABLE_HTTPS", "false").lower() == "true"
HTTP_PORT = int(os.getenv("HTTP_PORT", "8000"))
HTTPS_PORT = int(os.getenv("HTTPS_PORT", "443"))

# TLS 加密套件 (Mozilla Modern)
SSL_CIPHERS = ":".join([
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
])


def check_ssl_files() -> bool:
    """检查 SSL 证书文件"""
    if not SSL_KEYFILE.exists():
        print(f"❌ 缺少服务器私钥: {SSL_KEYFILE}")
        return False
    if not SSL_CERTFILE.exists():
        print(f"❌ 缺少服务器证书: {SSL_CERTFILE}")
        return False
    print(f"✅ SSL 证书检查通过")
    return True


def main():
    config = {
        "app": "app.main:app",
        "host": "0.0.0.0",
        "reload": os.getenv("DEBUG", "false").lower() == "true",
        "workers": int(os.getenv("WORKERS", "1")),
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "access_log": True,
    }
    
    if ENABLE_HTTPS:
        if not check_ssl_files():
            print("\n❌ SSL 证书文件缺失")
            print("请先运行: scripts/certs/generate_certs.sh")
            sys.exit(1)
        
        config.update({
            "port": HTTPS_PORT,
            "ssl_keyfile": str(SSL_KEYFILE),
            "ssl_certfile": str(SSL_CERTFILE),
            "ssl_ciphers": SSL_CIPHERS,
        })
        
        print(f"\n🔐 启动 HTTPS 服务")
        print(f"   地址: https://0.0.0.0:{HTTPS_PORT}")
        print(f"   证书: {SSL_CERTFILE}")
    else:
        config["port"] = HTTP_PORT
        print(f"\n⚠️  启动 HTTP 服务 (未加密)")
        print(f"   地址: http://0.0.0.0:{HTTP_PORT}")
        print("   设置 ENABLE_HTTPS=true 启用 HTTPS")
    
    print()
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
