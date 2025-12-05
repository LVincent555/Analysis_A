# -*- coding: utf-8 -*-
"""
业务审计日志 (Audit Log System)

双轨制日志设计:
1. 审计日志 (AuditLog) → PostgreSQL (给管理员看)
2. 系统日志 (Loguru) → 文件 (给开发者看)

特性:
- Write-Behind: 内存缓冲，批量写入
- 业务层透明: log() 调用微秒级返回
- 防溢出: 超过上限时丢弃最旧的
"""

import threading
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """
    审计日志条目
    
    使用 __slots__ 优化内存 (通过 dataclass slots=True in Python 3.10+)
    """
    user_id: int
    action: str         # login, logout, password_change, force_logout, etc.
    target: str = ""    # 操作对象 (如被踢的用户ID)
    detail: str = ""    # JSON 详情
    ip: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class AuditLogBuffer:
    """
    审计日志缓冲区 - Write-Behind 模式
    
    业务代码调用 log() 时，直接 push 到内存队列
    DatabaseSyncer 每 10 秒批量 Insert 到 operation_logs 表
    
    使用方式:
        from app.core.audit import audit_log
        
        audit_log.log(user.id, "login", ip=request.client.host)
        audit_log.log(admin.id, "force_logout", target=str(target_user_id))
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: 缓冲区最大容量，超过时丢弃最旧的
        """
        self._buffer: List[AuditLogEntry] = []
        self._lock = threading.Lock()
        self.max_size = max_size
    
    def log(
        self,
        user_id: int,
        action: str,
        target: str = "",
        detail: str = "",
        ip: str = ""
    ) -> None:
        """
        记录审计日志 (内存操作，微秒级)
        
        Args:
            user_id: 操作者用户ID
            action: 操作类型 (login, logout, password_change, force_logout, etc.)
            target: 操作对象 (如被踢的用户ID)
            detail: JSON 详情
            ip: 客户端IP
        """
        entry = AuditLogEntry(
            user_id=user_id,
            action=action,
            target=target,
            detail=detail,
            ip=ip
        )
        
        with self._lock:
            self._buffer.append(entry)
            # 防止内存溢出：超过上限时丢弃最旧的
            if len(self._buffer) > self.max_size:
                self._buffer.pop(0)
    
    def flush(self) -> List[AuditLogEntry]:
        """
        获取并清空缓冲区 (Syncer 调用)
        
        Returns:
            缓冲区中的所有日志条目
        """
        with self._lock:
            entries = self._buffer.copy()
            self._buffer.clear()
            return entries
    
    def stats(self) -> dict:
        """统计信息"""
        with self._lock:
            return {
                "pending": len(self._buffer),
                "max_size": self.max_size
            }
    
    def size(self) -> int:
        """当前缓冲区大小"""
        with self._lock:
            return len(self._buffer)


def create_audit_sync_callback(audit_buffer: AuditLogBuffer):
    """
    创建审计日志同步回调函数
    
    供 DatabaseSyncer 使用
    """
    def sync_audit_logs():
        entries = audit_buffer.flush()
        if not entries:
            return
        
        try:
            from ..database import SessionLocal
            from ..db_models import OperationLog
            
            db = SessionLocal()
            try:
                for entry in entries:
                    log = OperationLog(
                        user_id=entry.user_id,
                        action=entry.action,
                        target=entry.target,
                        detail=entry.detail,
                        ip_address=entry.ip,
                        created_at=entry.created_at
                    )
                    db.add(log)
                db.commit()
                logger.info(f"[AuditLog] Flushed {len(entries)} entries")
            except Exception as e:
                logger.error(f"[AuditLog] DB error: {e}")
                db.rollback()
            finally:
                db.close()
        except ImportError:
            logger.warning("[AuditLog] Database module not available")
    
    return sync_audit_logs


# 全局单例
audit_log = AuditLogBuffer()
