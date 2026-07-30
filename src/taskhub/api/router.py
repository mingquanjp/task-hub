"""Root HTTP router composition."""

from fastapi import APIRouter

from taskhub.api.system import router as system_router
from taskhub.api.v1.router import router as api_v1_router

router = APIRouter()
router.include_router(system_router)
router.include_router(api_v1_router)
