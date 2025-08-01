# schemas/project.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    # 前端不需要传 owner_id，由后端自动注入
    owner_id: Optional[int] = None
    package_path: Optional[str] = None


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    id: int
    package_path: str
    created_at: datetime
    owner_id: int  # 返回时可以包含 owner_id
    status: str
    version: Optional[str] = None
    entrypoint: str
    has_requirements: bool
    env_template: Optional[dict] = None

    class Config:
        from_attributes = True


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True