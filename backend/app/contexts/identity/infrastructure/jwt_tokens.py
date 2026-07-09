"""JWT token issuer adapter."""

import os
from datetime import datetime, timedelta

from jose import JWTError, jwt

from ....core.security_settings import get_jwt_secret
from ....shared.time import utc_now_naive


ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"
SECRET_KEY = get_jwt_secret()


class JwtTokenIssuer:
    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self,
        user_id: int,
        device_id: str = "default",
        expires_hours: int | None = None,
        token_version: int | None = None,
    ) -> str:
        now = utc_now_naive()
        expire = now + timedelta(hours=expires_hours or ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": str(user_id),
            "device": device_id,
            "exp": expire,
            "iat": now,
            "type": "access",
        }
        if token_version is not None:
            payload["ver"] = token_version
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: int,
        device_id: str = "default",
        expires_days: int | None = None,
        token_version: int | None = None,
    ) -> str:
        now = utc_now_naive()
        expire = now + timedelta(days=expires_days or REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": str(user_id),
            "device": device_id,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }
        if token_version is not None:
            payload["ver"] = token_version
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError as exc:
            print(f"JWT验证失败: {exc}")
            return None

    def get_token_expiry(self, token: str) -> datetime | None:
        payload = self.verify_token(token)
        if payload and "exp" in payload:
            return datetime.fromtimestamp(payload["exp"])
        return None


jwt_token_issuer = JwtTokenIssuer()
