# -*- coding: utf-8 -*-
"""
数据库同步器 (Database Syncer)

职责:
1. 定期扫描 Write-Behind 策略的脏数据
2. 批量更新到 PostgreSQL
3. 清理过期缓存
4. 智能GC：内存阈值触发 + 时间间隔触发
"""

import threading
import time
import logging
import gc
from typing import List, Callable, Optional

logger = logging.getLogger(__name__)


class DatabaseSyncer(threading.Thread):
    """
    数据库同步器 - 守护线程
    
    特性:
    - Write-Behind: 批量同步脏数据到DB
    - GC防抖: 内存>80%时激进GC，否则按时间间隔
    - 优雅关闭: force_sync 确保数据不丢失
    """
    
    # GC 触发阈值 (针对 2GB 服务器)
    MEMORY_THRESHOLD_PERCENT = 80
    
    def __init__(
        self, 
        sync_interval: int = 10, 
        gc_interval: int = 300,
        session_sync_callback: Optional[Callable] = None,
        audit_sync_callback: Optional[Callable] = None
    ):
        """
        Args:
            sync_interval: 同步间隔 (秒)，默认10秒
            gc_interval: GC间隔 (秒)，默认5分钟
            session_sync_callback: 会话同步回调函数
            audit_sync_callback: 审计日志同步回调函数
        """
        super().__init__()
        self.daemon = True  # 守护线程，主程序退出时自动退出
        self.running = True
        self.sync_interval = sync_interval
        self.gc_interval = gc_interval
        self._last_gc = time.time()
        
        # 回调函数
        self._session_sync_callback = session_sync_callback
        self._audit_sync_callback = audit_sync_callback
    
    def run(self):
        """主循环"""
        logger.info(f"[Syncer] Started, sync={self.sync_interval}s, gc={self.gc_interval}s")
        
        while self.running:
            time.sleep(self.sync_interval)
            try:
                self._sync_sessions()
                self._sync_audit_logs()
                self._maybe_gc()
            except Exception as e:
                logger.error(f"[Syncer] Error: {e}")
    
    def _sync_sessions(self):
        """同步会话数据到DB"""
        if self._session_sync_callback:
            try:
                self._session_sync_callback()
            except Exception as e:
                logger.error(f"[Syncer] Session sync error: {e}")
            return
        
        # 默认实现：使用 UnifiedCache
        try:
            from .manager import UnifiedCache
            from .policies.write_behind import WriteBehindPolicy
            
            if not UnifiedCache.has_region("sessions"):
                return
            
            store = UnifiedCache.session()
            policy = store.policy
            
            if not isinstance(policy, WriteBehindPolicy):
                return
            
            dirty_keys = policy.get_dirty_keys()
            if not dirty_keys:
                return
            
            # 构建批量更新数据
            mappings = []
            with store._lock:
                for key in dirty_keys:
                    entry = store.store.get(key)
                    if entry and entry.value:
                        v = entry.value
                        mappings.append({
                            "id": int(key),
                            "last_active": v.get("last_active"),
                            "current_status": self._status_to_str(v.get("status")),
                            "ip_address": v.get("ip_address", "")
                        })
                        entry.clear_dirty()
            
            if mappings:
                self._bulk_update_sessions(mappings)
                logger.info(f"[Syncer] Synced {len(mappings)} sessions")
        
        except Exception as e:
            logger.error(f"[Syncer] Session sync error: {e}")
    
    def _status_to_str(self, status: int) -> str:
        """状态码转字符串"""
        return {1: "online", 2: "idle", 3: "locked"}.get(status, "online")
    
    def _bulk_update_sessions(self, mappings: List[dict]):
        """批量更新会话到数据库"""
        try:
            from ...database import SessionLocal
            from ...db_models import UserSession
            from datetime import datetime
            
            db = SessionLocal()
            try:
                for m in mappings:
                    # 转换时间戳
                    if m.get("last_active"):
                        m["last_active"] = datetime.fromtimestamp(m["last_active"])
                
                db.bulk_update_mappings(UserSession, mappings)
                db.commit()
            finally:
                db.close()
        except ImportError:
            logger.warning("[Syncer] Database module not available, skipping sync")
        except Exception as e:
            logger.error(f"[Syncer] DB update error: {e}")
    
    def _sync_audit_logs(self):
        """同步审计日志到DB"""
        if self._audit_sync_callback:
            try:
                self._audit_sync_callback()
            except Exception as e:
                logger.error(f"[Syncer] Audit log sync error: {e}")
    
    def _maybe_gc(self):
        """
        智能GC：内存阈值防抖
        
        策略:
        1. 内存使用 > 80%：立即 GC (不管时间间隔)
        2. 内存使用 < 80%：按时间间隔 GC (避免频繁 GC 造成 CPU 抖动)
        """
        now = time.time()
        
        # 尝试获取内存信息
        mem_percent = self._get_memory_percent()
        
        # 条件1：内存压力大，激进GC
        need_gc_by_memory = mem_percent > self.MEMORY_THRESHOLD_PERCENT
        # 条件2：时间到了，常规GC
        need_gc_by_time = (now - self._last_gc) > self.gc_interval
        
        if need_gc_by_memory or need_gc_by_time:
            try:
                from .manager import UnifiedCache
                result = UnifiedCache.gc()
                
                reason = "memory_pressure" if need_gc_by_memory else "scheduled"
                logger.info(f"[Syncer] GC completed ({reason}, mem={mem_percent}%): {result}")
            except Exception as e:
                logger.error(f"[Syncer] GC error: {e}")
            
            self._last_gc = now
    
    def _get_memory_percent(self) -> float:
        """获取内存使用百分比"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            # psutil 未安装，返回 0 (永远不触发内存压力GC)
            return 0.0
    
    def stop(self):
        """停止同步器"""
        self.running = False
    
    def force_sync(self):
        """强制同步 (优雅关闭时调用)"""
        logger.info("[Syncer] Force sync triggered")
        self._sync_sessions()
        self._sync_audit_logs()
    
    def set_session_sync_callback(self, callback: Callable):
        """设置会话同步回调"""
        self._session_sync_callback = callback
    
    def set_audit_sync_callback(self, callback: Callable):
        """设置审计日志同步回调"""
        self._audit_sync_callback = callback


# 全局单例 (延迟启动)
_syncer: Optional[DatabaseSyncer] = None


def get_syncer() -> DatabaseSyncer:
    """获取同步器单例"""
    global _syncer
    if _syncer is None:
        _syncer = DatabaseSyncer()
    return _syncer


def start_syncer():
    """启动同步器"""
    syncer = get_syncer()
    if not syncer.is_alive():
        syncer.start()


def stop_syncer():
    """停止同步器"""
    global _syncer
    if _syncer is not None:
        _syncer.force_sync()
        _syncer.stop()
        _syncer = None
