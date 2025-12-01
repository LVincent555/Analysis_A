"""
初始化管理员账户脚本
首次部署时运行，创建默认管理员账户
"""
import sys
import os
import secrets
import string

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.db_models import User, Base
from app.auth.password import hash_password
from app.crypto.aes_handler import generate_key, get_master_crypto


def generate_random_password(length: int = 16) -> str:
    """生成随机密码"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def init_admin():
    """初始化管理员账户"""
    db = SessionLocal()
    
    try:
        # 检查是否已存在admin
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("⚠️  管理员账户已存在，跳过创建")
            print(f"   用户名: admin")
            print(f"   如需重置密码，请手动删除后重新运行此脚本")
            return None
        
        # 生成随机密码
        password = generate_random_password(16)
        
        # 生成用户密钥
        user_key = generate_key()
        master_crypto = get_master_crypto()
        user_key_encrypted = master_crypto.encrypt_key(user_key)
        
        # 创建管理员
        admin = User(
            username="admin",
            password_hash=hash_password(password),
            user_key_encrypted=user_key_encrypted,
            role="admin",
            is_active=True,
            allowed_devices=10,  # 管理员允许更多设备
            offline_enabled=True,
            offline_days=30  # 管理员离线天数更长
        )
        
        db.add(admin)
        db.commit()
        
        print("=" * 50)
        print("✅ 管理员账户创建成功！")
        print("=" * 50)
        print(f"   用户名: admin")
        print(f"   密码:   {password}")
        print("=" * 50)
        print("⚠️  请妥善保管此密码，首次登录后建议修改！")
        print("=" * 50)
        
        return password
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔧 初始化管理员账户...\n")
    init_admin()
