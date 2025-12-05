# -*- coding: utf-8 -*-
"""
统一缓存系统单元测试

运行方式:
    cd backend
    python -m pytest tests/test_caching.py -v
    
或单独运行:
    python tests/test_caching.py
"""

import sys
import os
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.caching.entry import CacheEntry
from app.core.caching.policy import CachePolicy
from app.core.caching.policies import WriteBehindPolicy, CacheAsidePolicy, WriteThroughPolicy
from app.core.caching.store import ObjectStore, FileStore
from app.core.caching.manager import UnifiedCache
from app.core.caching.facade import cache, KeyBuilder, safe_cache_call


class TestCacheEntry(unittest.TestCase):
    """测试 CacheEntry"""
    
    def test_basic_creation(self):
        """基本创建"""
        entry = CacheEntry("test_value", ttl=60)
        self.assertEqual(entry.value, "test_value")
        self.assertFalse(entry.is_expired())
        self.assertEqual(entry.version, 1)
    
    def test_expiration(self):
        """过期测试"""
        entry = CacheEntry("value", ttl=1)
        self.assertFalse(entry.is_expired())
        time.sleep(1.1)
        self.assertTrue(entry.is_expired())
    
    def test_no_expiration(self):
        """永不过期"""
        entry = CacheEntry("value", ttl=0)
        self.assertFalse(entry.is_expired())
        self.assertEqual(entry.remaining_ttl(), float('inf'))
    
    def test_dirty_flag(self):
        """脏数据标记"""
        entry = CacheEntry("value")
        self.assertFalse(entry.is_dirty)
        entry.mark_dirty()
        self.assertTrue(entry.is_dirty)
        entry.clear_dirty()
        self.assertFalse(entry.is_dirty)
    
    def test_version(self):
        """版本号"""
        entry = CacheEntry("value", version=5)
        self.assertEqual(entry.version, 5)
        self.assertFalse(entry.is_stale(5))
        self.assertTrue(entry.is_stale(6))
    
    def test_slots_memory(self):
        """验证 __slots__ 生效"""
        entry = CacheEntry("value")
        with self.assertRaises(AttributeError):
            entry.random_attr = "should fail"


class TestWriteBehindPolicy(unittest.TestCase):
    """测试 Write-Behind 策略"""
    
    def setUp(self):
        self.policy = WriteBehindPolicy(ttl=60)
        self.store = {}
    
    def test_set_marks_dirty(self):
        """写入标记脏数据"""
        self.policy.set("key1", "value1", self.store)
        self.assertIn("key1", self.store)
        self.assertTrue(self.store["key1"].is_dirty)
        self.assertIn("key1", self.policy.dirty_keys)
    
    def test_get_dirty_keys(self):
        """获取并清空脏数据"""
        self.policy.set("k1", "v1", self.store)
        self.policy.set("k2", "v2", self.store)
        
        dirty = self.policy.get_dirty_keys()
        self.assertEqual(dirty, {"k1", "k2"})
        self.assertEqual(len(self.policy.dirty_keys), 0)
    
    def test_get_returns_value(self):
        """读取返回值"""
        self.policy.set("key", "value", self.store)
        result = self.policy.get("key", self.store)
        self.assertEqual(result, "value")
    
    def test_get_expired_returns_none(self):
        """过期数据返回 None"""
        policy = WriteBehindPolicy(ttl=1)
        policy.set("key", "value", self.store)
        time.sleep(1.1)
        result = policy.get("key", self.store)
        self.assertIsNone(result)


class TestCacheAsidePolicy(unittest.TestCase):
    """测试 Cache-Aside 策略"""
    
    def setUp(self):
        self.policy = CacheAsidePolicy(ttl=60)
        self.store = {}
    
    def test_get_with_loader(self):
        """未命中时回源加载"""
        loader_called = [False]
        def loader():
            loader_called[0] = True
            return "loaded_value"
        
        result = self.policy.get("key", self.store, loader=loader)
        self.assertEqual(result, "loaded_value")
        self.assertTrue(loader_called[0])
        # 验证已缓存
        self.assertIn("key", self.store)
    
    def test_get_cached_no_loader_call(self):
        """命中时不调用 loader"""
        self.policy.set_direct("key", "cached", self.store)
        
        loader_called = [False]
        def loader():
            loader_called[0] = True
            return "new_value"
        
        result = self.policy.get("key", self.store, loader=loader)
        self.assertEqual(result, "cached")
        self.assertFalse(loader_called[0])
    
    def test_set_deletes_cache(self):
        """写入时删除缓存 (Lazy Load)"""
        self.policy.set_direct("key", "old", self.store)
        self.assertIn("key", self.store)
        
        self.policy.set("key", "new", self.store)
        self.assertNotIn("key", self.store)


class TestObjectStore(unittest.TestCase):
    """测试 ObjectStore"""
    
    def setUp(self):
        self.store = ObjectStore("test", WriteBehindPolicy(ttl=60))
    
    def test_basic_operations(self):
        """基本读写删"""
        self.store.set("k1", "v1")
        self.assertEqual(self.store.get("k1"), "v1")
        
        self.store.delete("k1")
        self.assertIsNone(self.store.get("k1"))
    
    def test_clear(self):
        """清空"""
        self.store.set("k1", "v1")
        self.store.set("k2", "v2")
        self.store.clear()
        self.assertEqual(self.store.size(), 0)
    
    def test_stats(self):
        """统计信息"""
        self.store.set("k1", "v1")
        stats = self.store.stats()
        self.assertEqual(stats["name"], "test")
        self.assertEqual(stats["type"], "object")
        self.assertEqual(stats["total"], 1)


class TestUnifiedCache(unittest.TestCase):
    """测试 UnifiedCache 管理器"""
    
    def setUp(self):
        # 清理之前的注册
        UnifiedCache._regions.clear()
        UnifiedCache._initialized = False
    
    def test_register_and_get(self):
        """注册和获取分区"""
        store = ObjectStore("sessions", WriteBehindPolicy())
        UnifiedCache.register("sessions", store)
        
        self.assertTrue(UnifiedCache.has_region("sessions"))
        self.assertEqual(UnifiedCache.get_region("sessions"), store)
    
    def test_get_nonexistent_raises(self):
        """获取不存在的分区抛异常"""
        with self.assertRaises(KeyError):
            UnifiedCache.get_region("nonexistent")
    
    def test_stats(self):
        """全局统计"""
        UnifiedCache.register("test1", ObjectStore("test1", WriteBehindPolicy()))
        UnifiedCache.register("test2", ObjectStore("test2", CacheAsidePolicy()))
        
        stats = UnifiedCache.stats()
        self.assertIn("test1", stats)
        self.assertIn("test2", stats)


class TestKeyBuilder(unittest.TestCase):
    """测试 KeyBuilder"""
    
    def test_session_key(self):
        self.assertEqual(KeyBuilder.session(123), "123")
    
    def test_user_key(self):
        self.assertEqual(KeyBuilder.user(456), "456")
    
    def test_api_key(self):
        self.assertEqual(KeyBuilder.api("daily", "abc123"), "api:daily:abc123")
    
    def test_hotspot_key(self):
        self.assertEqual(KeyBuilder.hotspot("2024-01-15"), "hotspot:2024-01-15")
    
    def test_signal_key(self):
        self.assertEqual(KeyBuilder.signal("danzhen", "2024-01-15"), "signal:danzhen:2024-01-15")


class TestSafeCacheCall(unittest.TestCase):
    """测试 safe_cache_call 装饰器"""
    
    def test_normal_return(self):
        """正常返回"""
        @safe_cache_call(default_return="default")
        def good_func():
            return "success"
        
        self.assertEqual(good_func(), "success")
    
    def test_exception_returns_default(self):
        """异常返回默认值"""
        @safe_cache_call(default_return="fallback")
        def bad_func():
            raise RuntimeError("Cache error")
        
        self.assertEqual(bad_func(), "fallback")
    
    def test_default_none(self):
        """默认返回 None"""
        @safe_cache_call()
        def bad_func():
            raise Exception("error")
        
        self.assertIsNone(bad_func())


class TestPublicCacheIntegration(unittest.TestCase):
    """测试 PublicCache 集成"""
    
    def setUp(self):
        """初始化测试环境"""
        UnifiedCache._regions.clear()
        UnifiedCache._initialized = False
        
        # 注册测试分区
        UnifiedCache.register("sessions", ObjectStore("sessions", WriteBehindPolicy(ttl=60)))
        UnifiedCache.register("users", ObjectStore("users", CacheAsidePolicy(ttl=60)))
        UnifiedCache.register("config", ObjectStore("config", CacheAsidePolicy(ttl=0)))
    
    def test_session_heartbeat(self):
        """会话心跳"""
        cache.set_session_heartbeat(1001, status=1, ip="192.168.1.1")
        
        session = cache.get_session(1001)
        self.assertIsNotNone(session)
        self.assertEqual(session["status"], 1)
        self.assertEqual(session["ip_address"], "192.168.1.1")
    
    def test_remove_session(self):
        """移除会话"""
        cache.set_session_heartbeat(1002, status=1, ip="127.0.0.1")
        self.assertIsNotNone(cache.get_session(1002))
        
        cache.remove_session(1002)
        self.assertIsNone(cache.get_session(1002))
    
    def test_user_with_loader(self):
        """用户信息回源"""
        def load_user():
            return {"id": 100, "name": "TestUser"}
        
        user = cache.get_user(100, loader=load_user)
        self.assertEqual(user["name"], "TestUser")
        
        # 第二次应该从缓存读取
        user2 = cache.get_user(100, loader=lambda: {"id": 100, "name": "Changed"})
        self.assertEqual(user2["name"], "TestUser")  # 仍是旧值
    
    def test_invalidate_user(self):
        """用户缓存失效"""
        cache.get_user(200, loader=lambda: {"id": 200, "name": "User200"})
        cache.invalidate_user(200)
        
        # 失效后重新加载
        user = cache.get_user(200, loader=lambda: {"id": 200, "name": "NewName"})
        self.assertEqual(user["name"], "NewName")
    
    def test_config(self):
        """配置缓存"""
        cache.set_config("app_name", "StockAnalysis")
        result = cache.get_config("app_name")
        self.assertEqual(result, "StockAnalysis")
    
    def test_stats(self):
        """统计接口"""
        stats = cache.stats()
        self.assertIn("sessions", stats)
        self.assertIn("users", stats)
    
    def test_gc(self):
        """GC 接口"""
        result = cache.gc()
        self.assertIsInstance(result, dict)


class TestFileStore(unittest.TestCase):
    """测试 FileStore (磁盘缓存)"""
    
    @classmethod
    def setUpClass(cls):
        """创建测试目录"""
        import tempfile
        cls.test_dir = tempfile.mkdtemp(prefix="cache_test_")
    
    @classmethod
    def tearDownClass(cls):
        """清理测试目录"""
        import shutil
        try:
            shutil.rmtree(cls.test_dir)
        except:
            pass
    
    def test_basic_operations(self):
        """基本读写"""
        store = FileStore("test_api", self.test_dir, size_limit_gb=0.01)
        
        store.set("key1", {"data": "value1"}, ttl=60)
        result = store.get("key1")
        self.assertEqual(result["data"], "value1")
    
    def test_get_with_loader(self):
        """未命中时回源"""
        store = FileStore("test_api2", os.path.join(self.test_dir, "api2"), size_limit_gb=0.01)
        
        loader_called = [False]
        def loader():
            loader_called[0] = True
            return {"loaded": True}
        
        result = store.get("new_key", loader=loader)
        self.assertTrue(loader_called[0])
        self.assertEqual(result["loaded"], True)
    
    def test_delete(self):
        """删除"""
        store = FileStore("test_api3", os.path.join(self.test_dir, "api3"), size_limit_gb=0.01)
        store.set("to_delete", "value")
        self.assertIsNotNone(store.get("to_delete"))
        
        store.delete("to_delete")
        self.assertIsNone(store.get("to_delete"))
    
    def test_stats(self):
        """统计信息"""
        store = FileStore("test_stats", os.path.join(self.test_dir, "stats"), size_limit_gb=0.01)
        store.set("k1", "v1")
        
        stats = store.stats()
        self.assertEqual(stats["type"], "disk")
        self.assertIn("size_mb", stats)
        self.assertIn("count", stats)


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("统一缓存系统单元测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestCacheEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestWriteBehindPolicy))
    suite.addTests(loader.loadTestsFromTestCase(TestCacheAsidePolicy))
    suite.addTests(loader.loadTestsFromTestCase(TestObjectStore))
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedCache))
    suite.addTests(loader.loadTestsFromTestCase(TestKeyBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestSafeCacheCall))
    suite.addTests(loader.loadTestsFromTestCase(TestPublicCacheIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestFileStore))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有测试通过!")
    else:
        print(f"❌ 失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
