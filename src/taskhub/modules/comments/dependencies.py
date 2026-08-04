"""FastAPI dependencies for comments."""

from typing import Annotated

from fastapi import Depends

from taskhub.api.dependencies import DbSessionDep
from taskhub.modules.comments.repository import CommentRepository
from taskhub.modules.comments.service import CommentService
from taskhub.modules.comments.sqlalchemy_repository import SQLAlchemyCommentRepository
from taskhub.modules.tasks.dependencies import TaskRepositoryDep


def get_comment_repository(session: DbSessionDep) -> CommentRepository:
    """Provide the comment repository."""
    return SQLAlchemyCommentRepository(session)


CommentRepositoryDep = Annotated[CommentRepository, Depends(get_comment_repository)]


def get_comment_service(
    comment_repo: CommentRepositoryDep,
    task_repo: TaskRepositoryDep,
) -> CommentService:
    """Provide the comment service."""
    return CommentService(comment_repo, task_repo)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
