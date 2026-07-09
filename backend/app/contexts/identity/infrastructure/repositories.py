"""SQLAlchemy adapters for identity repositories."""

import json
from datetime import datetime

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from ....db_models import OperationLog, Role, User, UserSession, user_roles


class SqlAlchemyIdentityUserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def add_user(self, username: str, password_hash: str, user_key_encrypted: str) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            user_key_encrypted=user_key_encrypted,
        )
        self.db.add(user)
        return user

    def refresh(self, entity) -> None:
        self.db.refresh(entity)

    def commit(self) -> None:
        self.db.commit()


class SqlAlchemyIdentitySessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_valid_refresh_session(
        self,
        user_id: int,
        device_id: str,
        refresh_token: str,
        now: datetime,
    ) -> UserSession | None:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.device_id == (device_id or "default"),
            UserSession.refresh_token == refresh_token,
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).first()

    def find_active_session(self, user_id: int, device_id: str, now: datetime) -> UserSession | None:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.device_id == (device_id or "default"),
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).first()

    def touch(self, session: UserSession, now: datetime) -> None:
        session.last_active = now

    def get_by_user_device(self, user_id: int, device_id: str) -> UserSession | None:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.device_id == (device_id or "default"),
        ).first()

    def count_active_for_user(self, user_id: int, now: datetime) -> int:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).count()

    def find_oldest_active_for_user(self, user_id: int, now: datetime) -> UserSession | None:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).order_by(UserSession.last_active.asc()).first()

    def list_active_for_user(self, user_id: int, now: datetime) -> list[UserSession]:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).all()

    def list_for_admin(
        self,
        *,
        page: int,
        page_size: int,
        user_id: int | None,
        username: str | None,
        include_expired: bool,
        include_revoked: bool,
        now: datetime,
    ) -> tuple[int, list[UserSession]]:
        query = self.db.query(UserSession).join(User)

        if not include_revoked:
            query = query.filter(UserSession.is_revoked == False)

        if not include_expired:
            query = query.filter(UserSession.expires_at > now)

        if user_id:
            query = query.filter(UserSession.user_id == user_id)

        if username:
            query = query.filter(User.username.ilike(f"%{username}%"))

        total = query.count()
        rows = (
            query.options(joinedload(UserSession.user))
            .order_by(desc(UserSession.last_active))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, rows

    def get_by_id(self, session_id: int) -> UserSession | None:
        return (
            self.db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(UserSession.id == session_id)
            .first()
        )

    def list_unrevoked_for_user(
        self,
        user_id: int,
        exclude_session_id: int | None = None,
    ) -> list[UserSession]:
        query = self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
        )
        if exclude_session_id is not None:
            query = query.filter(UserSession.id != exclude_session_id)
        return query.all()

    def list_active(self, now: datetime) -> list[UserSession]:
        return self.db.query(UserSession).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).all()

    def count_online_users(self, *, now: datetime, active_since: datetime) -> int:
        count = self.db.query(func.count(func.distinct(UserSession.user_id))).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
            UserSession.last_active > active_since,
        ).scalar()
        return count or 0

    def platform_distribution(self, now: datetime) -> dict[str, int]:
        rows = self.db.query(
            UserSession.platform,
            func.count(UserSession.id),
        ).filter(
            UserSession.is_revoked == False,
            UserSession.expires_at > now,
        ).group_by(UserSession.platform).all()
        return {platform or "unknown": count for platform, count in rows}

    def delete(self, session: UserSession) -> None:
        self.db.delete(session)

    def upsert_user_device_session(
        self,
        *,
        existing_session: UserSession | None,
        user_id: int,
        device_id: str,
        device_name: str | None,
        session_key_encrypted: str,
        refresh_token: str,
        expires_at: datetime,
        now: datetime,
    ) -> UserSession:
        if existing_session:
            existing_session.session_key_encrypted = session_key_encrypted
            existing_session.refresh_token = refresh_token
            existing_session.expires_at = expires_at
            existing_session.last_active = now
            existing_session.current_status = "online"
            existing_session.is_revoked = False
            existing_session.revoked_at = None
            existing_session.revoked_by = None
            if device_name:
                existing_session.device_name = device_name
            return existing_session

        session = UserSession(
            user_id=user_id,
            device_id=device_id or "default",
            device_name=device_name,
            session_key_encrypted=session_key_encrypted,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        self.db.add(session)
        return session

    def revoke_device(self, user_id: int, device_id: str, revoked_by: int, now: datetime) -> None:
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.device_id == (device_id or "default"),
            UserSession.is_revoked == False,
        ).update({
            "is_revoked": True,
            "revoked_at": now,
            "revoked_by": revoked_by,
        }, synchronize_session=False)

    def delete_all_for_user(self, user_id: int) -> None:
        self.db.query(UserSession).filter(UserSession.user_id == user_id).delete()

    def cleanup_expired_before(self, cutoff: datetime) -> int:
        return self.db.query(UserSession).filter(
            or_(
                UserSession.expires_at < cutoff,
                (
                    (UserSession.is_revoked == True)
                    & (UserSession.revoked_at < cutoff)
                ),
            )
        ).delete(synchronize_session=False)

    def commit(self) -> None:
        self.db.commit()


class SqlAlchemyIdentityUserQueryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        status: str | None,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
        now: datetime,
    ) -> tuple[int, list[User], dict[int, int]]:
        query = self.db.query(User)

        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern),
                )
            )

        if role:
            query = query.filter(User.role == role)

        if status:
            if status == "active":
                query = query.filter(
                    User.is_active == True,
                    or_(User.locked_until.is_(None), User.locked_until <= now),
                    or_(User.expires_at.is_(None), User.expires_at > now),
                )
            elif status == "inactive":
                query = query.filter(User.is_active == False)
            elif status == "locked":
                query = query.filter(User.locked_until > now)
            elif status == "expired":
                query = query.filter(User.expires_at <= now)

        total = query.count()
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        users = query.offset((page - 1) * page_size).limit(page_size).all()
        user_ids = [user.id for user in users]
        session_counts: dict[int, int] = {}
        if user_ids:
            rows = self.db.query(
                UserSession.user_id,
                func.count(UserSession.id),
            ).filter(
                UserSession.user_id.in_(user_ids),
                UserSession.is_revoked == False,
            ).group_by(UserSession.user_id).all()
            session_counts = {user_id: count for user_id, count in rows}

        return total, users, session_counts

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
        ).first()

    def list_unrevoked_sessions_for_user(self, user_id: int) -> list[UserSession]:
        return self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,
        ).order_by(UserSession.last_active.desc()).all()


class SqlAlchemyIdentityUserCommandRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
        ).first()

    def get_user_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_active_role_by_name(self, name: str) -> Role | None:
        return self.db.query(Role).filter(
            Role.name == name,
            Role.is_active == True,
        ).first()

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        user_key_encrypted: str,
        email: str | None,
        phone: str | None,
        nickname: str | None,
        role: str,
        allowed_devices: int,
        offline_enabled: bool,
        offline_days: int,
        expires_at: datetime | None,
        remark: str | None,
        created_by: int,
        now: datetime,
    ) -> User:
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
            created_by=created_by,
            password_changed_at=now,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def refresh(self, entity) -> None:
        self.db.refresh(entity)

    def clear_user_roles(self, user_id: int) -> None:
        self.db.execute(user_roles.delete().where(user_roles.c.user_id == user_id))

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        self.db.execute(user_roles.insert().values(user_id=user_id, role_id=role_id))

    def revoke_sessions_for_user(
        self,
        user_id: int,
        *,
        revoked_by: int,
        now: datetime,
        only_unrevoked: bool,
    ) -> None:
        query = self.db.query(UserSession).filter(UserSession.user_id == user_id)
        if only_unrevoked:
            query = query.filter(UserSession.is_revoked == False)
        query.update({
            "is_revoked": True,
            "revoked_at": now,
            "revoked_by": revoked_by,
        }, synchronize_session=False)

    def hard_delete_user(self, user: User) -> None:
        self.db.delete(user)

    def bulk_set_users_active(self, user_ids: list[int], is_active: bool, now: datetime) -> int:
        return self.db.query(User).filter(
            User.id.in_(user_ids),
            User.deleted_at.is_(None),
        ).update({
            "is_active": is_active,
            "updated_at": now,
        }, synchronize_session=False)

    def bulk_soft_delete_users(self, user_ids: list[int], now: datetime) -> int:
        return self.db.query(User).filter(
            User.id.in_(user_ids),
            User.deleted_at.is_(None),
        ).update({
            "deleted_at": now,
            "is_active": False,
            "updated_at": now,
        }, synchronize_session=False)

    def revoke_sessions_for_users(
        self,
        user_ids: list[int],
        *,
        revoked_by: int,
        now: datetime,
        only_unrevoked: bool,
    ) -> None:
        query = self.db.query(UserSession).filter(UserSession.user_id.in_(user_ids))
        if only_unrevoked:
            query = query.filter(UserSession.is_revoked == False)
        query.update({
            "is_revoked": True,
            "revoked_at": now,
            "revoked_by": revoked_by,
        }, synchronize_session=False)

    def commit(self) -> None:
        self.db.commit()


class SqlAlchemyIdentityAuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        log_type: str,
        action: str,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        ip_address: str | None = None,
        detail: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
    ) -> None:
        self.db.add(
            OperationLog(
                log_type=log_type,
                action=action,
                operator_id=operator_id,
                operator_name=operator_name,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                ip_address=ip_address,
                detail=json.dumps(detail, ensure_ascii=False) if detail else None,
                old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
                new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
                status=status,
            )
        )


class SqlAlchemyIdentityRoleQueryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self, include_inactive: bool) -> list[Role]:
        query = self.db.query(Role)
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        return query.order_by(Role.is_system.desc(), Role.id).all()

    def count_users_for_role(self, role_id: int) -> int:
        return self.db.query(user_roles).filter(
            user_roles.c.role_id == role_id,
        ).count()

    def get_role_by_id(self, role_id: int) -> Role | None:
        return (
            self.db.query(Role)
            .options(joinedload(Role.users))
            .filter(Role.id == role_id)
            .first()
        )

    def get_user_with_roles(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .options(joinedload(User.roles))
            .filter(User.id == user_id)
            .first()
        )

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_role_by_name(self, name: str) -> Role | None:
        return self.db.query(Role).filter(Role.name == name).first()

    def create_role(
        self,
        *,
        name: str,
        display_name: str,
        description: str | None,
        permissions: list[str],
    ) -> Role:
        role = Role(
            name=name,
            display_name=display_name,
            description=description,
            permissions=json.dumps(permissions, ensure_ascii=False),
            is_system=False,
            is_active=True,
        )
        self.db.add(role)
        self.db.flush()
        return role

    def set_role_permissions(self, role: Role, permissions: list[str]) -> None:
        role.permissions = json.dumps(permissions, ensure_ascii=False)

    def user_has_role(self, user_id: int, role_id: int) -> bool:
        return self.db.query(user_roles).filter(
            user_roles.c.user_id == user_id,
            user_roles.c.role_id == role_id,
        ).first() is not None

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        self.db.execute(user_roles.insert().values(user_id=user_id, role_id=role_id))

    def remove_role_from_user(self, user_id: int, role_id: int) -> None:
        self.db.execute(
            user_roles.delete().where(
                (user_roles.c.user_id == user_id)
                & (user_roles.c.role_id == role_id)
            )
        )

    def delete_role(self, role: Role) -> None:
        self.db.delete(role)

    def commit(self) -> None:
        self.db.commit()
