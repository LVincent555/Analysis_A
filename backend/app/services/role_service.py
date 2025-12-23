"""
角色权限服务
提供角色CRUD、权限验证等功能
v1.1.0
"""
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..db_models import Role, User, OperationLog, user_roles

logger = logging.getLogger(__name__)


# 所有权限定义
ALL_PERMISSIONS = {
    # 分析功能
    "analysis:hotspot": "最新热点分析",
    "analysis:industry": "行业趋势分析",
    "analysis:rank_jump": "排名跳变",
    "analysis:steady_rise": "稳步上升",
    "analysis:sector": "板块分析",
    "analysis:signal": "信号系统",
    "analysis:*": "所有分析功能",
    
    # 查询功能
    "query:stock": "股票查询",
    "query:sector": "板块查询",
    "query:*": "所有查询功能",
    
    # 数据管理
    "data:view": "查看数据管理",
    "data:import": "导入数据",
    "data:delete": "删除数据",
    "data:*": "所有数据功能",
    
    # 用户管理
    "user:view": "查看用户列表",
    "user:create": "创建用户",
    "user:update": "编辑用户",
    "user:delete": "删除用户",
    "user:reset_password": "重置密码",
    "user:*": "所有用户功能",
    
    # 会话管理
    "session:view": "查看会话列表",
    "session:force_logout": "强制下线",
    "session:*": "所有会话功能",
    
    # 日志管理
    "log:view": "查看操作日志",
    "log:export": "导出日志",
    "log:*": "所有日志功能",
    
    # 系统配置
    "config:view": "查看系统配置",
    "config:update": "修改系统配置",
    "config:*": "所有配置功能",
    
    # 角色管理
    "role:view": "查看角色列表",
    "role:create": "创建角色",
    "role:update": "编辑角色",
    "role:delete": "删除角色",
    "role:*": "所有角色功能",
    
    # 超级权限
    "*": "所有权限"
}


class RoleService:
    """角色权限服务"""
    
    @staticmethod
    def get_all_permissions() -> Dict[str, str]:
        """获取所有权限定义"""
        return ALL_PERMISSIONS
    
    @staticmethod
    def get_roles(
        db: Session,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """获取角色列表"""
        query = db.query(Role)
        
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        
        roles = query.order_by(Role.is_system.desc(), Role.id).all()
        
        result = []
        for role in roles:
            # 统计用户数
            user_count = db.query(user_roles).filter(
                user_roles.c.role_id == role.id
            ).count()
            
            role_dict = role.to_dict()
            role_dict["user_count"] = user_count
            result.append(role_dict)
        
        return result
    
    @staticmethod
    def get_role(db: Session, role_id: int) -> Optional[Dict[str, Any]]:
        """获取角色详情"""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return None
        
        # 获取拥有该角色的用户
        users = db.query(User).join(user_roles).filter(
            user_roles.c.role_id == role_id
        ).all()
        
        role_dict = role.to_dict()
        role_dict["users"] = [
            {"id": u.id, "username": u.username, "nickname": u.nickname}
            for u in users
        ]
        
        return role_dict
    
    @staticmethod
    def get_role_by_name(db: Session, name: str) -> Optional[Role]:
        """根据名称获取角色"""
        return db.query(Role).filter(Role.name == name).first()
    
    @staticmethod
    def create_role(
        db: Session,
        name: str,
        display_name: str,
        description: Optional[str],
        permissions: List[str],
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建角色"""
        # 检查名称是否已存在
        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            raise ValueError(f"角色名称已存在: {name}")
        
        # 创建角色
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            permissions=json.dumps(permissions),
            is_system=False,
            is_active=True
        )
        db.add(role)
        db.flush()
        
        # 记录日志
        log = OperationLog(
            log_type="USER",
            action="role_create",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="role",
            target_id=role.id,
            target_name=name,
            ip_address=ip_address,
            new_value=json.dumps({
                "name": name,
                "display_name": display_name,
                "permissions": permissions
            }),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"角色已创建: {name} (by {operator_name})")
        
        return {
            "success": True,
            "message": "角色创建成功",
            "role_id": role.id
        }
    
    @staticmethod
    def update_role(
        db: Session,
        role_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        operator_id: int = None,
        operator_name: str = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新角色"""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("角色不存在")
        
        # 系统角色限制修改
        if role.is_system and permissions is not None:
            raise ValueError("系统预设角色的权限不可修改")
        
        # 记录旧值
        old_value = {
            "display_name": role.display_name,
            "description": role.description,
            "permissions": role.get_permissions(),
            "is_active": role.is_active
        }
        
        # 更新字段
        if display_name is not None:
            role.display_name = display_name
        if description is not None:
            role.description = description
        if permissions is not None:
            role.permissions = json.dumps(permissions)
        if is_active is not None:
            role.is_active = is_active
        
        role.updated_at = datetime.utcnow()
        
        # 记录日志
        new_value = {
            "display_name": role.display_name,
            "description": role.description,
            "permissions": role.get_permissions(),
            "is_active": role.is_active
        }
        
        log = OperationLog(
            log_type="USER",
            action="role_update",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="role",
            target_id=role_id,
            target_name=role.name,
            ip_address=ip_address,
            old_value=json.dumps(old_value),
            new_value=json.dumps(new_value),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"角色已更新: {role.name} (by {operator_name})")
        
        return {
            "success": True,
            "message": "角色更新成功"
        }
    
    @staticmethod
    def delete_role(
        db: Session,
        role_id: int,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """删除角色"""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("角色不存在")
        
        if role.is_system:
            raise ValueError("系统预设角色不可删除")
        
        # 检查是否有用户使用该角色
        user_count = db.query(user_roles).filter(
            user_roles.c.role_id == role_id
        ).count()
        
        if user_count > 0:
            raise ValueError(f"该角色下还有 {user_count} 个用户，请先移除用户")
        
        role_name = role.name
        
        # 删除角色
        db.delete(role)
        
        # 记录日志
        log = OperationLog(
            log_type="USER",
            action="role_delete",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="role",
            target_id=role_id,
            target_name=role_name,
            ip_address=ip_address,
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"角色已删除: {role_name} (by {operator_name})")
        
        return {
            "success": True,
            "message": "角色删除成功"
        }
    
    @staticmethod
    def assign_role_to_user(
        db: Session,
        user_id: int,
        role_id: int,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """为用户分配角色"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")
        
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("角色不存在")
        
        # 检查是否已分配
        existing = db.query(user_roles).filter(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id
        ).first()
        
        if existing:
            return {
                "success": True,
                "message": "用户已拥有该角色"
            }
        
        # 分配角色
        db.execute(user_roles.insert().values(
            user_id=user_id,
            role_id=role_id
        ))
        
        # 记录日志
        log = OperationLog(
            log_type="USER",
            action="role_assign",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="user",
            target_id=user_id,
            target_name=user.username,
            ip_address=ip_address,
            detail=json.dumps({"role_id": role_id, "role_name": role.name}),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"角色已分配: {user.username} <- {role.name} (by {operator_name})")
        
        return {
            "success": True,
            "message": f"已为用户分配角色: {role.display_name}"
        }
    
    @staticmethod
    def remove_role_from_user(
        db: Session,
        user_id: int,
        role_id: int,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """移除用户的角色"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")
        
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError("角色不存在")
        
        # 删除关联
        db.execute(user_roles.delete().where(
            and_(
                user_roles.c.user_id == user_id,
                user_roles.c.role_id == role_id
            )
        ))
        
        # 记录日志
        log = OperationLog(
            log_type="USER",
            action="role_remove",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="user",
            target_id=user_id,
            target_name=user.username,
            ip_address=ip_address,
            detail=json.dumps({"role_id": role_id, "role_name": role.name}),
            status="success"
        )
        db.add(log)
        db.commit()
        
        logger.info(f"角色已移除: {user.username} -x- {role.name} (by {operator_name})")
        
        return {
            "success": True,
            "message": f"已移除用户角色: {role.display_name}"
        }
    
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> List[str]:
        """获取用户的所有权限（合并所有角色）"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        # 从 user.role 字段获取基础权限（兼容旧逻辑）
        if user.role == 'admin':
            return ["*"]
        
        # 从角色表获取权限
        permissions = set()
        for role in user.roles:
            if role.is_active:
                perms = role.get_permissions()
                if "*" in perms:
                    return ["*"]
                permissions.update(perms)
        
        return list(permissions)
    
    @staticmethod
    def check_permission(db: Session, user_id: int, permission: str) -> bool:
        """检查用户是否有指定权限"""
        permissions = RoleService.get_user_permissions(db, user_id)
        
        if "*" in permissions:
            return True
        
        if permission in permissions:
            return True
        
        # 检查通配符
        prefix = permission.split(":")[0] + ":*"
        return prefix in permissions
