"""
会话管理服务
提供会话查询、状态监控、强制下线等功能
v1.1.0
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..db_models import User, UserSession, OperationLog

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""
    
    # 状态判定阈值（秒）
    ACTIVE_THRESHOLD = 120      # 2分钟内 = 活跃
    LOST_THRESHOLD = 300        # 2-5分钟 = 失联
    IDLE_THRESHOLD = 1800       # 5-30分钟 = 空闲/锁屏
    # 超过30分钟 = 离线
    
    @staticmethod
    def get_session_display_status(session: UserSession) -> Dict[str, str]:
        """
        根据会话信息判断显示状态
        返回: {"status": "active", "color": "green", "label": "活跃"}
        """
        now = datetime.utcnow()
        
        # 已撤销的会话
        if session.is_revoked:
            return {"status": "revoked", "color": "gray", "label": "已撤销"}
        
        # 已过期的会话
        if session.expires_at and session.expires_at < now:
            return {"status": "expired", "color": "gray", "label": "已过期"}
        
        # 计算空闲时间
        last_active = session.last_active or session.created_at
        if not last_active:
            return {"status": "unknown", "color": "gray", "label": "未知"}
        
        idle_seconds = (now - last_active).total_seconds()
        client_status = session.current_status or "online"
        
        if idle_seconds <= SessionService.ACTIVE_THRESHOLD:
            # 2分钟内
            if client_status == "locked":
                return {"status": "locked", "color": "gray", "label": "锁屏"}
            elif client_status == "idle":
                return {"status": "idle", "color": "yellow", "label": "空闲"}
            else:
                return {"status": "active", "color": "green", "label": "活跃"}
        
        elif idle_seconds <= SessionService.LOST_THRESHOLD:
            # 2-5分钟 = 失联
            return {"status": "lost", "color": "red", "label": "失联"}
        
        elif idle_seconds <= SessionService.IDLE_THRESHOLD:
            # 5-30分钟
            if client_status == "locked":
                return {"status": "locked", "color": "gray", "label": "锁屏"}
            else:
                return {"status": "idle", "color": "yellow", "label": "空闲"}
        
        else:
            # 超过30分钟 = 离线
            return {"status": "offline", "color": "black", "label": "离线"}
    
    @staticmethod
    def get_sessions(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        status: Optional[str] = None,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> Dict[str, Any]:
        """
        获取会话列表
        
        Args:
            status: active/idle/locked/lost/offline/all
        """
        query = db.query(UserSession).join(User)
        
        # 默认排除已撤销
        if not include_revoked:
            query = query.filter(UserSession.is_revoked == False)
        
        # 默认排除已过期
        if not include_expired:
            query = query.filter(UserSession.expires_at > datetime.utcnow())
        
        # 用户筛选
        if user_id:
            query = query.filter(UserSession.user_id == user_id)
        
        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))
        
        # 获取总数
        total = query.count()
        
        # 排序和分页
        query = query.order_by(desc(UserSession.last_active))
        offset = (page - 1) * page_size
        sessions = query.offset(offset).limit(page_size).all()
        
        # 构建结果
        items = []
        for session in sessions:
            display_status = SessionService.get_session_display_status(session)
            
            # 状态筛选（在内存中进行，因为状态是计算出来的）
            if status and status != 'all' and display_status['status'] != status:
                continue
            
            items.append({
                "id": session.id,
                "user_id": session.user_id,
                "username": session.user.username if session.user else None,
                "nickname": session.user.nickname if session.user else None,
                "device_id": session.device_id,
                "device_name": session.device_name,
                "ip_address": session.ip_address,
                "platform": session.platform,
                "app_version": session.app_version,
                "location": session.location,
                "status": display_status['status'],
                "status_color": display_status['color'],
                "status_label": display_status['label'],
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_active": session.last_active.isoformat() if session.last_active else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "is_revoked": session.is_revoked,
            })
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    
    @staticmethod
    def get_session_detail(db: Session, session_id: int) -> Optional[Dict[str, Any]]:
        """获取会话详情"""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not session:
            return None
        
        display_status = SessionService.get_session_display_status(session)
        
        return {
            "id": session.id,
            "user_id": session.user_id,
            "username": session.user.username if session.user else None,
            "nickname": session.user.nickname if session.user else None,
            "user_role": session.user.role if session.user else None,
            "device_id": session.device_id,
            "device_name": session.device_name,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "platform": session.platform,
            "app_version": session.app_version,
            "location": session.location,
            "status": display_status['status'],
            "status_color": display_status['color'],
            "status_label": display_status['label'],
            "current_status": session.current_status,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_active": session.last_active.isoformat() if session.last_active else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "is_revoked": session.is_revoked,
            "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
            "revoked_by": session.revoked_by,
        }
    
    @staticmethod
    def revoke_session(
        db: Session,
        session_id: int,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        撤销（强制下线）指定会话
        """
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not session:
            raise ValueError("会话不存在")
        
        if session.is_revoked:
            raise ValueError("会话已被撤销")
        
        # 不能撤销自己的会话
        if session.user_id == operator_id:
            raise ValueError("不能撤销自己的会话")
        
        # 获取目标用户信息
        target_user = session.user
        
        # 撤销会话
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        session.revoked_by = operator_id
        
        # 增加用户的 token_version，使所有旧 Token 失效
        if target_user:
            target_user.token_version = (target_user.token_version or 1) + 1
        
        # 记录操作日志
        log = OperationLog(
            log_type="SESSION",
            action="session_revoke",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="session",
            target_id=session_id,
            target_name=f"{target_user.username if target_user else 'unknown'}@{session.device_name or session.device_id}",
            ip_address=ip_address,
            detail=json.dumps({
                "device_id": session.device_id,
                "device_name": session.device_name,
                "user_id": session.user_id
            }),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"会话已撤销: session_id={session_id}, operator={operator_name}")
        
        return {
            "success": True,
            "message": "会话已撤销",
            "session_id": session_id
        }
    
    @staticmethod
    def revoke_user_all_sessions(
        db: Session,
        user_id: int,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None,
        exclude_current: bool = False,
        current_session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        撤销指定用户的所有会话
        """
        # 不能撤销自己的所有会话（除非 exclude_current=True）
        if user_id == operator_id and not exclude_current:
            raise ValueError("不能撤销自己的所有会话")
        
        # 获取目标用户
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise ValueError("用户不存在")
        
        # 查询该用户的活跃会话
        query = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False
        )
        
        # 排除当前会话
        if exclude_current and current_session_id:
            query = query.filter(UserSession.id != current_session_id)
        
        sessions = query.all()
        
        if not sessions:
            return {
                "success": True,
                "message": "没有需要撤销的会话",
                "affected": 0
            }
        
        # 批量撤销
        now = datetime.utcnow()
        affected = 0
        for session in sessions:
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_by = operator_id
            affected += 1
        
        # 增加用户的 token_version
        target_user.token_version = (target_user.token_version or 1) + 1
        
        # 记录操作日志
        log = OperationLog(
            log_type="SESSION",
            action="session_revoke_all",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="user",
            target_id=user_id,
            target_name=target_user.username,
            ip_address=ip_address,
            detail=json.dumps({
                "affected_sessions": affected,
                "exclude_current": exclude_current
            }),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"用户所有会话已撤销: user_id={user_id}, affected={affected}, operator={operator_name}")
        
        return {
            "success": True,
            "message": f"已撤销 {affected} 个会话",
            "affected": affected
        }
    
    @staticmethod
    def get_session_statistics(db: Session) -> Dict[str, Any]:
        """
        获取会话统计信息
        """
        now = datetime.utcnow()
        
        # 活跃会话（未撤销、未过期）
        active_query = db.query(UserSession).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now
        )
        
        total_active = active_query.count()
        
        # 按状态统计（需要在内存中计算）
        sessions = active_query.all()
        status_counts = {
            "active": 0,
            "idle": 0,
            "locked": 0,
            "lost": 0,
            "offline": 0
        }
        
        for session in sessions:
            display_status = SessionService.get_session_display_status(session)
            status = display_status['status']
            if status in status_counts:
                status_counts[status] += 1
        
        # 在线用户数（去重）
        online_users = db.query(func.count(func.distinct(UserSession.user_id))).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
            UserSession.last_active > now - timedelta(minutes=5)
        ).scalar()
        
        # 平台分布
        platform_stats = db.query(
            UserSession.platform,
            func.count(UserSession.id)
        ).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now
        ).group_by(UserSession.platform).all()
        
        platforms = {p[0] or "unknown": p[1] for p in platform_stats}
        
        return {
            "total_sessions": total_active,
            "online_users": online_users or 0,
            "status_distribution": status_counts,
            "platform_distribution": platforms,
            "updated_at": now.isoformat()
        }
    
    @staticmethod
    def update_session_heartbeat(
        db: Session,
        session_id: int,
        status: int = 1,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        更新会话心跳
        
        Args:
            status: 1=active, 2=idle, 3=locked
        """
        status_map = {1: "online", 2: "idle", 3: "locked"}
        
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if not session or session.is_revoked:
            return False
        
        session.last_active = datetime.utcnow()
        session.current_status = status_map.get(status, "online")
        
        if ip_address:
            session.ip_address = ip_address
        
        db.commit()
        return True
    
    @staticmethod
    def cleanup_expired_sessions(db: Session, days: int = 30) -> int:
        """
        清理过期会话（硬删除超过指定天数的会话）
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = db.query(UserSession).filter(
            or_(
                UserSession.expires_at < cutoff,
                and_(
                    UserSession.is_revoked == True,
                    UserSession.revoked_at < cutoff
                )
            )
        ).delete(synchronize_session=False)
        
        db.commit()
        
        if deleted > 0:
            logger.info(f"清理了 {deleted} 个过期会话")
        
        return deleted
