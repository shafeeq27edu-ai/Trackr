from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import uuid

from db.database import get_db
from db.models import Project, User
from db.schemas import ProjectCreate, ProjectResponse
from api.deps import get_current_user
from services.audit_service import log_audit_event

router = APIRouter()


@router.post("", response_model=ProjectResponse)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        id=str(uuid.uuid4()),
        name=project_in.name,
        description=project_in.description,
        user_id=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    await log_audit_event(db, current_user.id, "CREATE_PROJECT", project.id)
    return project


@router.get("", response_model=List[ProjectResponse])
async def get_projects(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Project).filter(Project.user_id == current_user.id))
    return result.scalars().all()


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).filter(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    await log_audit_event(db, current_user.id, "DELETE_PROJECT", project_id)
    return {"message": "Project deleted"}
