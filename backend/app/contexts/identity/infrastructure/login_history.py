"""SQL adapter for admin login history."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ....db_models import User, UserSession


class SqlLoginHistoryAdapter:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_login_history(self) -> dict[str, Any]:
        users_query = (
            self.db.query(
                User.id,
                User.username,
                User.role,
                User.is_active,
                User.created_at,
                User.last_login,
                func.count(UserSession.id).label("session_count"),
            )
            .outerjoin(UserSession, User.id == UserSession.user_id)
            .group_by(User.id)
            .order_by(User.last_login.desc().nullslast())
            .all()
        )

        users = [
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "session_count": user.session_count or 0,
            }
            for user in users_query
        ]

        sessions_query = (
            self.db.query(
                UserSession.id,
                UserSession.user_id,
                UserSession.device_id,
                UserSession.device_name,
                UserSession.created_at,
                UserSession.expires_at,
                UserSession.last_active,
                User.username,
                User.role,
            )
            .join(User, UserSession.user_id == User.id)
            .order_by(UserSession.last_active.desc().nullslast())
            .all()
        )
        sessions = [
            {
                "id": session.id,
                "user_id": session.user_id,
                "username": session.username,
                "role": session.role,
                "device_id": session.device_id,
                "device_name": session.device_name,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "last_active": session.last_active.isoformat() if session.last_active else None,
            }
            for session in sessions_query
        ]

        active_threshold = datetime.now() - timedelta(hours=24)
        session_active_threshold = datetime.now() - timedelta(hours=1)
        active_users = sum(
            1 for user in users if user["last_login"] and datetime.fromisoformat(user["last_login"]) > active_threshold
        )
        active_sessions = sum(
            1
            for session in sessions
            if session["last_active"] and datetime.fromisoformat(session["last_active"]) > session_active_threshold
        )

        return {
            "success": True,
            "data": {
                "users": users,
                "sessions": sessions,
                "stats": {
                    "totalUsers": len(users),
                    "activeUsers": active_users,
                    "totalSessions": len(sessions),
                    "activeSessions": active_sessions,
                },
            },
        }
