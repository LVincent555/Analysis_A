#!/usr/bin/env python
"""
用户管理 API 测试脚本
测试 Phase 1 用户管理功能
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
TOKEN = None


def login():
    """登录获取 Token"""
    global TOKEN
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"  # 请替换为实际密码
    })
    if resp.status_code == 200:
        TOKEN = resp.json().get("access_token")
        print(f"✅ 登录成功")
        return True
    else:
        print(f"❌ 登录失败: {resp.status_code} - {resp.text}")
        return False


def get_headers():
    """获取认证头"""
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def test_get_users():
    """测试获取用户列表"""
    print("\n📋 测试: 获取用户列表")
    resp = requests.get(
        f"{BASE_URL}/api/admin/users",
        headers=get_headers(),
        params={"page": 1, "page_size": 10}
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  ✅ 成功: 共 {data['total']} 个用户")
        for user in data['items'][:3]:
            print(f"     - {user['username']} ({user['role']}) - {user['status']}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_get_user_detail(user_id: int):
    """测试获取用户详情"""
    print(f"\n📋 测试: 获取用户详情 (ID={user_id})")
    resp = requests.get(
        f"{BASE_URL}/api/admin/users/{user_id}",
        headers=get_headers()
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"  ✅ 成功: {data['username']}")
        print(f"     角色: {data['role']}")
        print(f"     状态: {data['status']}")
        print(f"     会话数: {len(data.get('sessions', []))}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_create_user():
    """测试创建用户"""
    print("\n📋 测试: 创建用户")
    resp = requests.post(
        f"{BASE_URL}/api/admin/users",
        headers=get_headers(),
        json={
            "username": "test_user_001",
            "password": "test123456",
            "email": "test@example.com",
            "nickname": "测试用户",
            "role": "user",
            "remark": "API测试创建"
        }
    )
    if resp.status_code == 200:
        print(f"  ✅ 成功: {resp.json()['message']}")
        return True
    elif resp.status_code == 409:
        print(f"  ⚠️ 用户已存在: {resp.json()['detail']}")
        return True  # 不算失败
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_update_user(user_id: int):
    """测试更新用户"""
    print(f"\n📋 测试: 更新用户 (ID={user_id})")
    resp = requests.put(
        f"{BASE_URL}/api/admin/users/{user_id}",
        headers=get_headers(),
        json={
            "nickname": "更新后的昵称",
            "remark": "API测试更新"
        }
    )
    if resp.status_code == 200:
        print(f"  ✅ 成功: {resp.json()['message']}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_toggle_status(user_id: int, is_active: bool):
    """测试切换用户状态"""
    action = "启用" if is_active else "禁用"
    print(f"\n📋 测试: {action}用户 (ID={user_id})")
    resp = requests.post(
        f"{BASE_URL}/api/admin/users/{user_id}/toggle-status",
        headers=get_headers(),
        json={"is_active": is_active}
    )
    if resp.status_code == 200:
        print(f"  ✅ 成功: {resp.json()['message']}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_reset_password(user_id: int):
    """测试重置密码"""
    print(f"\n📋 测试: 重置密码 (ID={user_id})")
    resp = requests.post(
        f"{BASE_URL}/api/admin/users/{user_id}/reset-password",
        headers=get_headers(),
        json={
            "new_password": "newpass123",
            "force_logout": False
        }
    )
    if resp.status_code == 200:
        print(f"  ✅ 成功: {resp.json()['message']}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def test_delete_user(user_id: int):
    """测试删除用户"""
    print(f"\n📋 测试: 删除用户 (ID={user_id})")
    resp = requests.delete(
        f"{BASE_URL}/api/admin/users/{user_id}",
        headers=get_headers(),
        params={"hard": False}  # 软删除
    )
    if resp.status_code == 200:
        print(f"  ✅ 成功: {resp.json()['message']}")
        return True
    else:
        print(f"  ❌ 失败: {resp.status_code} - {resp.text}")
        return False


def main():
    print("=" * 60)
    print("用户管理 API 测试")
    print("=" * 60)
    
    # 1. 登录
    if not login():
        print("\n⚠️ 请先确保服务器运行且有管理员账户")
        sys.exit(1)
    
    # 2. 获取用户列表
    test_get_users()
    
    # 3. 获取用户详情（ID=1，通常是admin）
    test_get_user_detail(1)
    
    # 4. 创建测试用户
    test_create_user()
    
    # 5. 再次获取列表，找到测试用户
    resp = requests.get(
        f"{BASE_URL}/api/admin/users",
        headers=get_headers(),
        params={"search": "test_user_001"}
    )
    if resp.status_code == 200:
        users = resp.json()['items']
        if users:
            test_user_id = users[0]['id']
            print(f"\n找到测试用户 ID: {test_user_id}")
            
            # 6. 更新用户
            test_update_user(test_user_id)
            
            # 7. 禁用用户
            test_toggle_status(test_user_id, False)
            
            # 8. 启用用户
            test_toggle_status(test_user_id, True)
            
            # 9. 重置密码
            test_reset_password(test_user_id)
            
            # 10. 删除用户
            test_delete_user(test_user_id)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
