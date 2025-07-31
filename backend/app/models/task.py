# /app/models/task.py
from typing import Optional, List
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, func, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.models.project import Project
from app.models.task_run import TaskRun, TaskRunStatus


class TaskPriority(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Task(Base):
    __tablename__ = "cp_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("cp_projects.id"), nullable=False)
    spider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(50), comment="CRON表达式")
    args: Mapped[Optional[dict]] = mapped_column(JSON, comment="执行参数")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # ✅ 新增字段
    priority: Mapped[TaskPriority] = mapped_column(
        SqlEnum(TaskPriority, name="task_priority_enum"),
        default=TaskPriority.MEDIUM
    )
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=3600, comment="任务超时时间")
    max_retries: Mapped[int] = mapped_column(Integer, default=0, comment="失败后最大重试次数")
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True, comment="失败时通知")
    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False, comment="成功时通知")
    notification_emails: Mapped[Optional[list]] = mapped_column(JSON, comment="通知邮箱列表")
    last_run_status: Mapped[Optional[TaskRunStatus]] = mapped_column(
        SqlEnum(TaskRunStatus, name="task_run_status_enum"),
        comment="最近一次执行状态"
    )
    last_run_time: Mapped[Optional[DateTime]] = mapped_column(DateTime, comment="最近一次执行时间")

    # 关系
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    runs: Mapped[List["TaskRun"]] = relationship("TaskRun", back_populates="task", cascade="all, delete-orphan")