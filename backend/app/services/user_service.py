"""
用户管理服务
v1.1.0: 提供用户CRUD、状态管理、密码管理等功能
"""
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
import bcrypt

from ..db_models import User, UserSession, OperationLog
from ..crypto.aes_handler import generate_key, get_master_crypto

logger = logging.getLogger(__name__)


class UserService:
    """用户管理服务"""
    
    @staticmethod
    def get_users(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        获取用户列表（分页）
        
        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            search: 搜索关键词（用户名/邮箱/昵称）
            role: 角色筛选
            status: 状态筛选 (active/inactive/locked/expired)
            sort_by: 排序字段
            sort_order: 排序方向 (asc/desc)
            include_deleted: 是否包含已删除用户
        
        Returns:
            分页结果字典
        """
        query = db.query(User)
        
        # 默认不包含已删除用户
        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))
        
        # 搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern)
                )
            )
        
        # 角色筛选
        if role:
            query = query.filter(User.role == role)
        
        # 状态筛选
        if status:
            now = datetime.utcnow()
            if status == "active":
                query = query.filter(
                    User.is_active == True,
                    or_(User.locked_until.is_(None), User.locked_until <= now),
                    or_(User.expires_at.is_(None), User.expires_at > now)
                )
            elif status == "inactive":
                query = query.filter(User.is_active == False)
            elif status == "locked":
                query = query.filter(User.locked_until > now)
            elif status == "expired":
                query = query.filter(User.expires_at <= now)
        
        # 总数
        total = query.count()
        
        # 排序
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # 分页
        offset = (page - 1) * page_size
        users = query.offset(offset).limit(page_size).all()
        
        # 获取每个用户的活跃会话数
        user_ids = [u.id for u in users]
        session_counts = {}
        if user_ids:
            counts = db.query(
                UserSession.user_id,
                func.count(UserSession.id)
            ).filter(
                UserSession.user_id.in_(user_ids),
                UserSession.is_revoked == False
            ).group_by(UserSession.user_id).all()
            session_counts = {uid: count for uid, count in counts}
        
        # 构建结果
        items = []
        for user in users:
            item = user.to_dict_simple()
            item["active_sessions"] = session_counts.get(user.id, 0)
            items.append(item)
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items
        }
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None)
        ).first()
    
    @staticmethod
    def get_user_detail(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户详情（包含会话信息）"""
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        result = user.to_dict(include_sessions=True)
        
        # 获取会话列表
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False
        ).order_by(UserSession.last_active.desc()).all()
        
        result["sessions"] = [s.to_dict() for s in sessions]
        
        return result
    
    @staticmethod
    def create_user(
        db: Session,
        username: str,
        password: str,
        operator: User,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        nickname: Optional[str] = None,
        role: str = "user",
        allowed_devices: int = 3,
        offline_enabled: bool = True,
        offline_days: int = 7,
        expires_at: Optional[datetime] = None,
        remark: Optional[str] = None
    ) -> User:
        """
        创建用户
        
        Args:
            db: 数据库会话
            username: 用户名
            password: 明文密码
            operator: 操作者
            其他参数: 用户信息
        
        Returns:
            创建的用户对象
        
        Raises:
            ValueError: 用户名已存在
        """
        # 检查用户名是否存在
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError(f"用户名 '{username}' 已存在")
        
        # 生成密码哈希
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # 生成用户密钥
        user_key = generate_key()
        master_crypto = get_master_crypto()
        user_key_encrypted = master_crypto.encrypt_key(user_key)
        
        # 创建用户
        user = User(
            username=username,
            password_hash=password_hash,
            user_key_encrypted=user_key_encrypted,
            email=email,
            phone=phone,
            nickname=nickname or username,
            role=role,
            is_active=True,
            allowed_devices=allowed_devices,
            offline_enabled=offline_enabled,
            offline_days=offline_days,
            expires_at=expires_at,
            remark=remark,
            created_by=operator.id,
            password_changed_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 记录操作日志
        UserService._log_operation(
            db=db,
            log_type="USER",
            action="user_create",
            operator=operator,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            new_value={"username": username, "role": role}
        )
        
        logger.info(f"用户创建成功: {username} (by {operator.username})")
        return user
    
    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        operator: User,
        **kwargs
    ) -> User:
        """
        更新用户信息
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            operator: 操作者
            **kwargs: 要更新的字段
        
        Returns:
            更新后的用户对象
        
        Raises:
            ValueError: 用户不存在或操作非法
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 记录旧值
        old_value = {}
        new_value = {}
        
        # 允许更新的字段
        allowed_fields = [
            'email', 'phone', 'nickname', 'avatar_url', 'remark',
            'role', 'allowed_devices', 'offline_enabled', 'offline_days',
            'expires_at'
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                old_val = getattr(user, field)
                new_val = kwargs[field]
                
                # 特殊处理 expires_at
                if field == 'expires_at' and isinstance(new_val, str):
                    new_val = datetime.fromisoformat(new_val.replace('Z', '+00:00'))
                
                if old_val != new_val:
                    old_value[field] = str(old_val) if old_val else None
                    new_value[field] = str(new_val) if new_val else None
                    setattr(user, field, new_val)
        
        if new_value:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            # 记录操作日志
            UserService._log_operation(
                db=db,
                log_type="USER",
                action="user_update",
                operator=operator,
                target_type="user",
                target_id=user.id,
                target_name=user.username,
                old_value=old_value,
                new_value=new_value
            )
            
            logger.info(f"用户更新成功: {user.username} (by {operator.username})")
        
        return user
    
    @staticmethod
    def delete_user(
        db: Session,
        user_id: int,
        operator: User,
        hard_delete: bool = False
    ) -> bool:
        """
        删除用户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            operator: 操作者
            hard_delete: 是否硬删除
        
        Returns:
            是否成功
        
        Raises:
            ValueError: 用户不存在或操作非法
        """
        if user_id == operator.id:
            raise ValueError("不能删除自己的账户")
        
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        username = user.username
        
        if hard_delete:
            # 硬删除：彻底删除用户和所有会话
            db.delete(user)
        else:
            # 软删除：标记删除时间
            user.deleted_at = datetime.utcnow()
            user.is_active = False
            # 撤销所有会话
            db.query(UserSession).filter(
                UserSession.user_id == user_id
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.utcnow(),
                "revoked_by": operator.id
            })
        
        db.commit()
        
        # 记录操作日志
        UserService._log_operation(
            db=db,
            log_type="USER",
            action="user_delete",
            operator=operator,
            target_type="user",
            target_id=user_id,
            target_name=username,
            detail={"hard_delete": hard_delete}
        )
        
        logger.info(f"用户删除成功: {username} (by {operator.username}, hard={hard_delete})")
        return True
    
    @staticmethod
    def toggle_user_status(
        db: Session,
        user_id: int,
        operator: User,
        is_active: bool
    ) -> User:
        """
        启用/禁用用户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            operator: 操作者
            is_active: 是否启用
        
        Returns:
            更新后的用户对象
        """
        if user_id == operator.id:
            raise ValueError("不能禁用自己的账户")
        
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        old_status = user.is_active
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        
        # 如果禁用，撤销所有会话
        if not is_active:
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.utcnow(),
                "revoked_by": operator.id
            })
        
        db.commit()
        db.refresh(user)
        
        # 记录操作日志
        action = "user_enable" if is_active else "user_disable"
        UserService._log_operation(
            db=db,
            log_type="USER",
            action=action,
            operator=operator,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            old_value={"is_active": old_status},
            new_value={"is_active": is_active}
        )
        
        logger.info(f"用户状态变更: {user.username} -> {is_active} (by {operator.username})")
        return user
    
    @staticmethod
    def reset_password(
        db: Session,
        user_id: int,
        operator: User,
        new_password: str,
        force_logout: bool = True
    ) -> bool:
        """
        重置用户密码
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            operator: 操作者
            new_password: 新密码
            force_logout: 是否强制登出所有设备
        
        Returns:
            是否成功
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 生成新密码哈希
        password_hash = bcrypt.hashpw(
            new_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        user.password_hash = password_hash
        user.password_changed_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # 重置登录失败计数
        user.failed_attempts = 0
        user.locked_until = None
        
        # 强制登出
        if force_logout:
            user.token_version += 1
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.utcnow(),
                "revoked_by": operator.id
            })
        
        db.commit()
        
        # 记录操作日志
        UserService._log_operation(
            db=db,
            log_type="SECURITY",
            action="password_reset",
            operator=operator,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            detail={"force_logout": force_logout}
        )
        
        logger.info(f"密码重置成功: {user.username} (by {operator.username})")
        return True
    
    @staticmethod
    def unlock_user(
        db: Session,
        user_id: int,
        operator: User
    ) -> User:
        """
        解锁用户账户
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            operator: 操作者
        
        Returns:
            更新后的用户对象
        """
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        user.failed_attempts = 0
        user.locked_until = None
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        # 记录操作日志
        UserService._log_operation(
            db=db,
            log_type="SECURITY",
            action="account_unlocked",
            operator=operator,
            target_type="user",
            target_id=user.id,
            target_name=user.username
        )
        
        logger.info(f"用户解锁成功: {user.username} (by {operator.username})")
        return user
    
    @staticmethod
    def batch_operation(
        db: Session,
        user_ids: List[int],
        action: str,
        operator: User
    ) -> int:
        """
        批量操作用户
        
        Args:
            db: 数据库会话
            user_ids: 用户ID列表
            action: 操作类型 (enable/disable/delete)
            operator: 操作者
        
        Returns:
            影响的用户数
        """
        # 排除操作者自己
        user_ids = [uid for uid in user_ids if uid != operator.id]
        
        if not user_ids:
            return 0
        
        affected = 0
        
        if action == "enable":
            affected = db.query(User).filter(
                User.id.in_(user_ids),
                User.deleted_at.is_(None)
            ).update({"is_active": True, "updated_at": datetime.utcnow()}, synchronize_session=False)
        
        elif action == "disable":
            affected = db.query(User).filter(
                User.id.in_(user_ids),
                User.deleted_at.is_(None)
            ).update({"is_active": False, "updated_at": datetime.utcnow()}, synchronize_session=False)
            
            # 撤销所有会话
            db.query(UserSession).filter(
                UserSession.user_id.in_(user_ids),
                UserSession.is_revoked == False
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.utcnow(),
                "revoked_by": operator.id
            }, synchronize_session=False)
        
        elif action == "delete":
            affected = db.query(User).filter(
                User.id.in_(user_ids),
                User.deleted_at.is_(None)
            ).update({
                "deleted_at": datetime.utcnow(),
                "is_active": False,
                "updated_at": datetime.utcnow()
            }, synchronize_session=False)
            
            # 撤销所有会话
            db.query(UserSession).filter(
                UserSession.user_id.in_(user_ids)
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.utcnow(),
                "revoked_by": operator.id
            }, synchronize_session=False)
        
        db.commit()
        
        # 记录操作日志
        UserService._log_operation(
            db=db,
            log_type="USER",
            action=f"batch_{action}",
            operator=operator,
            detail={"user_ids": user_ids, "affected": affected}
        )
        
        logger.info(f"批量操作完成: {action} {affected}个用户 (by {operator.username})")
        return affected
    
    @staticmethod
    def _log_operation(
        db: Session,
        log_type: str,
        action: str,
        operator: User,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        detail: Optional[Dict] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录操作日志"""
        log = OperationLog(
            log_type=log_type,
            action=action,
            operator_id=operator.id if operator else None,
            operator_name=operator.username if operator else "system",
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
            new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
            status=status,
            error_message=error_message
        )
        db.add(log)
        # 不单独commit，由调用者统一commit
