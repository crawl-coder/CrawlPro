# /app/schemas/task.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class TaskRunBase(BaseModel):
    name: str
    project_id: int
    spider_name: str
    cron_expression: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    is_enabled: bool = True


class TaskRunCreate(TaskRunBase):
    name: str
    project_id: int
    spider_name: str


class TaskRunUpdate(TaskRunBase):
    name: Optional[str] = None
    task_id: int
    celery_task_id: str
    project_id: Optional[int] = None
    spider_name: Optional[str] = None
    worker_node: Optional[str] = None
    cron_expression: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class TaskRunOut(TaskRunBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2