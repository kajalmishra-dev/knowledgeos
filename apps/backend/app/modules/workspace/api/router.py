from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.workspace.application.services.workspace_service import (
    WorkspaceNotFoundError,
    WorkspaceService,
)
from app.modules.workspace.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(session: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(session)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: UserModel = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    workspace = await service.create(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: UserModel = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[WorkspaceResponse]:
    workspaces = await service.list_for_owner(current_user.id)
    return [WorkspaceResponse.model_validate(item) for item in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    try:
        workspace = await service.get_for_owner(workspace_id, current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    current_user: UserModel = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    if payload.name is None and payload.description is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    try:
        workspace = await service.update(
            workspace_id,
            current_user.id,
            name=payload.name,
            description=payload.description,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    try:
        await service.delete(workspace_id, current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
