"""Version 1 router composition."""

from fastapi import APIRouter

from taskhub.modules.auth.router import router as auth_router
from taskhub.modules.labels.router import router as labels_router
from taskhub.modules.users.router import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(labels_router)
