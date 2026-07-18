from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspace.infrastructure.models.workspace import WorkspaceModel


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
    ) -> WorkspaceModel:
        workspace = WorkspaceModel(owner_id=owner_id, name=name, description=description)
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def list_for_owner(self, owner_id: UUID) -> list[WorkspaceModel]:
        result = await self._session.execute(
            select(WorkspaceModel)
            .where(WorkspaceModel.owner_id == owner_id)
            .order_by(WorkspaceModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_owner(self, workspace_id: UUID, owner_id: UUID) -> WorkspaceModel:
        workspace = await self._session.get(WorkspaceModel, workspace_id)
        if workspace is None or workspace.owner_id != owner_id:
            raise WorkspaceNotFoundError("Workspace not found.")
        return workspace

    async def update(
        self,
        workspace_id: UUID,
        owner_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> WorkspaceModel:
        workspace = await self.get_for_owner(workspace_id, owner_id)
        if name is not None:
            workspace.name = name
        if description is not None:
            workspace.description = description
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def delete(self, workspace_id: UUID, owner_id: UUID) -> None:
        workspace = await self.get_for_owner(workspace_id, owner_id)
        await self._session.delete(workspace)
