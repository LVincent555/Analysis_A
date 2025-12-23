"""
操作日志服务
提供日志查询、统计、导出等功能
v1.1.0
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, cast, Date

from ..db_models import OperationLog, User

logger = logging.getLogger(__name__)


# 日志类型定义
LOG_TYPES = {
    "LOGIN": "登录日志",
    "USER": "用户操作",
    "SESSION": "会话操作",
    "SECURITY": "安全事件",
    "SYSTEM": "系统操作"
}

# 操作动作定义
LOG_ACTIONS = {
    # 登录相关
    "login_success": "登录成功",
    "login_failed": "登录失败",
    "logout": "登出",
    "token_refresh": "刷新令牌",
    "session_expired": "会话过期",
    
    # 用户管理
    "user_create": "创建用户",
    "user_update": "更新用户",
    "user_delete": "删除用户",
    "user_enable": "启用用户",
    "user_disable": "禁用用户",
    "password_reset": "重置密码",
    "password_change": "修改密码",
    "user_unlock": "解锁用户",
    
    # 会话管理
    "session_revoke": "撤销会话",
    "session_revoke_all": "撤销所有会话",
    
    # 安全事件
    "account_locked": "账户锁定",
    "account_unlocked": "账户解锁",
    "suspicious_login": "可疑登录",
    
    # 系统配置
    "config_update": "更新配置"
}


class LogService:
    """操作日志服务"""
    
    @staticmethod
    def get_logs(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        log_type: Optional[str] = None,
        action: Optional[str] = None,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取操作日志列表
        """
        query = db.query(OperationLog)
        
        # 日志类型筛选
        if log_type:
            query = query.filter(OperationLog.log_type == log_type)
        
        # 操作动作筛选
        if action:
            query = query.filter(OperationLog.action == action)
        
        # 操作者筛选
        if operator_id:
            query = query.filter(OperationLog.operator_id == operator_id)
        
        if operator_name:
            query = query.filter(OperationLog.operator_name.ilike(f"%{operator_name}%"))
        
        # 目标筛选
        if target_type:
            query = query.filter(OperationLog.target_type == target_type)
        
        if target_id:
            query = query.filter(OperationLog.target_id == target_id)
        
        # 状态筛选
        if status:
            query = query.filter(OperationLog.status == status)
        
        # 日期范围筛选
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(OperationLog.created_at >= start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(OperationLog.created_at < end)
            except ValueError:
                pass
        
        # 关键词搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    OperationLog.operator_name.ilike(search_pattern),
                    OperationLog.target_name.ilike(search_pattern),
                    OperationLog.ip_address.ilike(search_pattern),
                    OperationLog.detail.ilike(search_pattern)
                )
            )
        
        # 获取总数
        total = query.count()
        
        # 排序和分页
        query = query.order_by(desc(OperationLog.created_at))
        offset = (page - 1) * page_size
        logs = query.offset(offset).limit(page_size).all()
        
        # 构建结果
        items = []
        for log in logs:
            items.append({
                "id": log.id,
                "log_type": log.log_type,
                "log_type_label": LOG_TYPES.get(log.log_type, log.log_type),
                "action": log.action,
                "action_label": LOG_ACTIONS.get(log.action, log.action),
                "operator_id": log.operator_id,
                "operator_name": log.operator_name or "系统",
                "target_type": log.target_type,
                "target_id": log.target_id,
                "target_name": log.target_name,
                "ip_address": log.ip_address,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    
    @staticmethod
    def get_log_detail(db: Session, log_id: int) -> Optional[Dict[str, Any]]:
        """获取日志详情"""
        log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
        if not log:
            return None
        
        # 解析 JSON 字段
        detail = None
        old_value = None
        new_value = None
        
        try:
            if log.detail:
                detail = json.loads(log.detail) if isinstance(log.detail, str) else log.detail
        except:
            detail = log.detail
        
        try:
            if log.old_value:
                old_value = json.loads(log.old_value) if isinstance(log.old_value, str) else log.old_value
        except:
            old_value = log.old_value
        
        try:
            if log.new_value:
                new_value = json.loads(log.new_value) if isinstance(log.new_value, str) else log.new_value
        except:
            new_value = log.new_value
        
        return {
            "id": log.id,
            "log_type": log.log_type,
            "log_type_label": LOG_TYPES.get(log.log_type, log.log_type),
            "action": log.action,
            "action_label": LOG_ACTIONS.get(log.action, log.action),
            "operator_id": log.operator_id,
            "operator_name": log.operator_name or "系统",
            "target_type": log.target_type,
            "target_id": log.target_id,
            "target_name": log.target_name,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "detail": detail,
            "old_value": old_value,
            "new_value": new_value,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
    
    @staticmethod
    def get_log_statistics(
        db: Session,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取日志统计信息
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # 按类型统计
        type_stats = db.query(
            OperationLog.log_type,
            func.count(OperationLog.id)
        ).filter(
            OperationLog.created_at >= start_date
        ).group_by(OperationLog.log_type).all()
        
        type_distribution = {
            t[0]: {"count": t[1], "label": LOG_TYPES.get(t[0], t[0])}
            for t in type_stats
        }
        
        # 按状态统计
        status_stats = db.query(
            OperationLog.status,
            func.count(OperationLog.id)
        ).filter(
            OperationLog.created_at >= start_date
        ).group_by(OperationLog.status).all()
        
        status_distribution = {s[0]: s[1] for s in status_stats}
        
        # 按日期统计（最近7天趋势）
        daily_stats = db.query(
            cast(OperationLog.created_at, Date),
            func.count(OperationLog.id)
        ).filter(
            OperationLog.created_at >= start_date
        ).group_by(
            cast(OperationLog.created_at, Date)
        ).order_by(
            cast(OperationLog.created_at, Date)
        ).all()
        
        daily_trend = [
            {"date": d[0].isoformat() if d[0] else None, "count": d[1]}
            for d in daily_stats
        ]
        
        # 登录失败统计
        login_failed_count = db.query(func.count(OperationLog.id)).filter(
            OperationLog.action == "login_failed",
            OperationLog.created_at >= start_date
        ).scalar() or 0
        
        # 安全事件统计
        security_count = db.query(func.count(OperationLog.id)).filter(
            OperationLog.log_type == "SECURITY",
            OperationLog.created_at >= start_date
        ).scalar() or 0
        
        # 总数
        total = db.query(func.count(OperationLog.id)).filter(
            OperationLog.created_at >= start_date
        ).scalar() or 0
        
        return {
            "period_days": days,
            "total": total,
            "type_distribution": type_distribution,
            "status_distribution": status_distribution,
            "daily_trend": daily_trend,
            "login_failed_count": login_failed_count,
            "security_event_count": security_count,
            "updated_at": now.isoformat()
        }
    
    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取指定用户的操作记录
        """
        query = db.query(OperationLog).filter(
            or_(
                OperationLog.operator_id == user_id,
                and_(
                    OperationLog.target_type == "user",
                    OperationLog.target_id == user_id
                )
            )
        )
        
        total = query.count()
        
        query = query.order_by(desc(OperationLog.created_at))
        offset = (page - 1) * page_size
        logs = query.offset(offset).limit(page_size).all()
        
        items = []
        for log in logs:
            items.append({
                "id": log.id,
                "log_type": log.log_type,
                "action": log.action,
                "action_label": LOG_ACTIONS.get(log.action, log.action),
                "operator_name": log.operator_name or "系统",
                "target_name": log.target_name,
                "ip_address": log.ip_address,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "is_operator": log.operator_id == user_id
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    
    @staticmethod
    def export_logs(
        db: Session,
        log_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        导出日志（用于下载）
        """
        query = db.query(OperationLog)
        
        if log_type:
            query = query.filter(OperationLog.log_type == log_type)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(OperationLog.created_at >= start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(OperationLog.created_at < end)
            except ValueError:
                pass
        
        query = query.order_by(desc(OperationLog.created_at)).limit(limit)
        logs = query.all()
        
        return [
            {
                "时间": log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else "",
                "类型": LOG_TYPES.get(log.log_type, log.log_type),
                "操作": LOG_ACTIONS.get(log.action, log.action),
                "操作者": log.operator_name or "系统",
                "目标": log.target_name or "",
                "IP地址": log.ip_address or "",
                "状态": "成功" if log.status == "success" else "失败",
                "错误信息": log.error_message or ""
            }
            for log in logs
        ]
    
    @staticmethod
    def cleanup_old_logs(db: Session, days: int = 90) -> int:
        """
        清理旧日志
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = db.query(OperationLog).filter(
            OperationLog.created_at < cutoff
        ).delete(synchronize_session=False)
        
        db.commit()
        
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条旧日志")
        
        return deleted
    
    @staticmethod
    def log_operation(
        db: Session,
        log_type: str,
        action: str,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        detail: Optional[Dict] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> OperationLog:
        """
        记录操作日志（通用方法）
        """
        log = OperationLog(
            log_type=log_type,
            action=action,
            operator_id=operator_id,
            operator_name=operator_name,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=json.dumps(detail) if detail else None,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            status=status,
            error_message=error_message
        )
        db.add(log)
        db.commit()
        
        return log
