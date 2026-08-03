"""Version 1 router composition."""

from fastapi import APIRouter

from taskhub.modules.auth.router import router as auth_router
from taskhub.modules.labels.router import router as labels_router
from taskhub.modules.projects.router import router as projects_router
from taskhub.modules.projects.router import workspace_projects_router
from taskhub.modules.users.router import router as users_router
from taskhub.modules.workspaces.router import router as workspaces_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(labels_router)
router.include_router(workspaces_router)
router.include_router(projects_router)
router.include_router(workspace_projects_router)
