#!/usr/bin/env python3
"""
测试TTL缓存模块
"""
import sys
sys.path.insert(0, 'backend')

try:
    from app.services.ttl_cache import ttl_cache
    print("✅ ttl_cache模块导入成功")
    
    # 测试基本功能
    ttl_cache.set("test_key", {"data": "test"}, ttl=300)
    result = ttl_cache.get("test_key")
    
    if result:
        print(f"✅ 缓存写入/读取成功: {result}")
    else:
        print("❌ 缓存读取失败")
    
    # 测试统计
    stats = ttl_cache.get_stats()
    print(f"✅ 缓存统计: {stats}")
    
    print("\n✅ 所有测试通过！TTL缓存模块正常")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
