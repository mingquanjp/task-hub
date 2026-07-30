"""Persistence contract and in-memory implementation for labels."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from taskhub.modules.labels.entities import Label


class LabelRepository(Protocol):
    """Storage operations required by the label application service."""

    async def create(self, label: Label) -> Label:
        """Store a new label."""

    async def list_by_project(self, project_id: UUID) -> Sequence[Label]:
        """Return all labels belonging to a project."""

    async def get_by_id(self, label_id: UUID) -> Label | None:
        """Return a label by ID when it exists."""

    async def update(self, label: Label) -> Label:
        """Store the supplied label state."""

    async def delete(self, label_id: UUID) -> bool:
        """Delete a label and report whether it existed."""


class InMemoryLabelRepository:
    """Application-scoped label storage intended for the initial API slice."""

    def __init__(self) -> None:
        self._labels: dict[UUID, Label] = {}

    async def create(self, label: Label) -> Label:
        """Store a new label."""
        self._labels[label.id] = label
        return label

    async def list_by_project(self, project_id: UUID) -> Sequence[Label]:
        """Return labels for the requested project."""
        return [label for label in self._labels.values() if label.project_id == project_id]

    async def get_by_id(self, label_id: UUID) -> Label | None:
        """Return a label by ID when it exists."""
        return self._labels.get(label_id)

    async def update(self, label: Label) -> Label:
        """Store the supplied label state."""
        self._labels[label.id] = label
        return label

    async def delete(self, label_id: UUID) -> bool:
        """Delete a label and report whether it existed."""
        return self._labels.pop(label_id, None) is not None
