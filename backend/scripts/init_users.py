"""
用户管理脚本
支持交互式创建用户，不硬编码任何密码

用法:
  python scripts/init_users.py              # 交互式创建用户
  python scripts/init_users.py --auto       # 自动创建默认用户（随机密码）
"""
import sys
import os
import secrets
import string
import getpass
import argparse

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


def create_user(db, username: str, password: str = None, role: str = "user", 
                allowed_devices: int = 3, offline_days: int = 7) -> tuple:
    """
    创建用户
    返回: (成功标志, 密码或错误信息)
    """
    try:
        # 检查是否已存在
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return False, f"用户 {username} 已存在"
        
        # 生成密码（如果未提供）
        if not password:
            password = generate_random_password(16)
        
        # 生成用户密钥
        user_key = generate_key()
        master_crypto = get_master_crypto()
        user_key_encrypted = master_crypto.encrypt_key(user_key)
        
        # 创建用户
        user = User(
            username=username,
            password_hash=hash_password(password),
            user_key_encrypted=user_key_encrypted,
            role=role,
            is_active=True,
            allowed_devices=allowed_devices,
            offline_enabled=True,
            offline_days=offline_days
        )
        
        db.add(user)
        db.commit()
        
        return True, password
        
    except Exception as e:
        db.rollback()
        return False, str(e)


def interactive_create_user(db):
    """交互式创建单个用户"""
    print("\n" + "=" * 50)
    print("👤 创建新用户")
    print("=" * 50)
    
    # 输入用户名
    while True:
        username = input("\n用户名: ").strip()
        if not username:
            print("❌ 用户名不能为空")
            continue
        
        # 检查是否已存在
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"❌ 用户 {username} 已存在")
            continue
        break
    
    # 输入密码
    while True:
        password = getpass.getpass("密码 (留空自动生成): ")
        if not password:
            password = generate_random_password(16)
            print(f"� 自动生成密码: {password}")
            break
        
        password_confirm = getpass.getpass("确认密码: ")
        if password != password_confirm:
            print("❌ 两次密码不一致")
            continue
        break
    
    # 选择角色
    role = input("角色 [user/admin] (默认 user): ").strip().lower()
    if role not in ['admin', 'user']:
        role = 'user'
    
    # 设置权限
    if role == 'admin':
        allowed_devices = 10
        offline_days = 30
    else:
        allowed_devices = 3
        offline_days = 7
    
    # 创建用户
    success, result = create_user(
        db, username, password, role, allowed_devices, offline_days
    )
    
    if success:
        print(f"\n✅ 用户 {username} 创建成功！")
        print(f"   角色: {role}")
        print(f"   密码: {result}")
        return True
    else:
        print(f"\n❌ 创建失败: {result}")
        return False


def auto_create_users(db):
    """自动创建默认用户（全部使用随机密码）"""
    print("\n" + "=" * 60)
    print("🔧 自动创建默认用户（随机密码）")
    print("=" * 60 + "\n")
    
    results = []
    
    # 创建 admin
    print("📌 创建 admin 账户...")
    success, result = create_user(db, "admin", None, "admin", 10, 30)
    if success:
        print(f"   ✅ 创建成功，密码: {result}")
        results.append(("admin", result, "admin"))
    else:
        print(f"   ⚠️  {result}")
    
    # 创建 user
    print("📌 创建 user 账户...")
    success, result = create_user(db, "user", None, "user", 3, 7)
    if success:
        print(f"   ✅ 创建成功，密码: {result}")
        results.append(("user", result, "user"))
    else:
        print(f"   ⚠️  {result}")
    
    # 输出汇总
    if results:
        print("\n" + "=" * 60)
        print("📋 用户账户汇总")
        print("=" * 60)
        print(f"{'用户名':<15} {'密码':<25} {'角色':<10}")
        print("-" * 60)
        for username, password, role in results:
            print(f"{username:<15} {password:<25} {role:<10}")
        print("=" * 60)
        print("\n⚠️  请妥善保管以上密码！")
    
    return results


def list_users(db):
    """列出所有用户"""
    users = db.query(User).all()
    
    print("\n" + "=" * 60)
    print("� 用户列表")
    print("=" * 60)
    print(f"{'ID':<5} {'用户名':<15} {'角色':<10} {'状态':<10} {'创建时间'}")
    print("-" * 60)
    
    for user in users:
        status = "✅ 启用" if user.is_active else "❌ 禁用"
        created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
        print(f"{user.id:<5} {user.username:<15} {user.role:<10} {status:<10} {created}")
    
    print("=" * 60)
    print(f"共 {len(users)} 个用户\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="用户管理工具")
    parser.add_argument('--auto', action='store_true', help='自动创建默认用户（随机密码）')
    parser.add_argument('--list', action='store_true', help='列出所有用户')
    args = parser.parse_args()
    
    db = SessionLocal()
    
    # 确保表存在
    Base.metadata.create_all(bind=engine)
    
    try:
        if args.list:
            list_users(db)
        elif args.auto:
            auto_create_users(db)
        else:
            # 交互式菜单
            print("\n" + "=" * 50)
            print("🔧 用户管理工具")
            print("=" * 50)
            print("1. 创建新用户")
            print("2. 列出所有用户")
            print("3. 自动创建默认用户 (admin + user)")
            print("0. 退出")
            
            while True:
                choice = input("\n请选择 [0-3]: ").strip()
                
                if choice == '1':
                    interactive_create_user(db)
                elif choice == '2':
                    list_users(db)
                elif choice == '3':
                    auto_create_users(db)
                elif choice == '0':
                    print("👋 再见！\n")
                    break
                else:
                    print("❌ 无效选择")
    finally:
        db.close()


if __name__ == "__main__":
    main()
