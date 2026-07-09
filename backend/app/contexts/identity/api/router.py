"""Identity context API composition."""

from fastapi import APIRouter

from .auth_router import router as auth_router
from .role_router import router as role_router
from .session_router import router as session_router
from .user_router import router as user_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(session_router)
router.include_router(role_router)
