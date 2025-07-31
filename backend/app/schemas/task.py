# /app/schemas/task.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class TaskBase(BaseModel):
    name: str
    project_id: int
    spider_name: str
    cron_expression: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    is_enabled: bool = True


class TaskCreate(TaskBase):
    name: str
    project_id: int
    spider_name: str


class TaskUpdate(TaskBase):
    name: Optional[str] = None
    project_id: Optional[int] = None
    spider_name: Optional[str] = None
    cron_expression: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class TaskOut(TaskBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2