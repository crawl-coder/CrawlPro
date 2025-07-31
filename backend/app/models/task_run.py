# /backend/app/models/task_run.py
from typing import Optional

from enum import Enum as PyEnum  # ✅ Python 枚举
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum as SqlEnum, Text, Float, Boolean  # ✅ SQL 列类型
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class TaskRunStatus(str, PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class TaskRun(Base):
    __tablename__ = "cp_task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("cp_tasks.id"), nullable=False)
    celery_task_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[TaskRunStatus] = mapped_column(
        SqlEnum(TaskRunStatus, name="task_run_status_enum"),
        default=TaskRunStatus.PENDING
    )
    start_time: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    end_time: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    log_output: Mapped[Optional[str]] = mapped_column(Text)
    worker_node: Mapped[Optional[str]] = mapped_column(String(100))

    # ✅ 新增字段
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, comment="进程退出码")
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, comment="CPU 使用率 (%)")
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, comment="内存使用 (MB)")
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, comment="执行时长")
    items_scraped: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="抓取条数")
    requests_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, comment="请求数")
    result_size_mb: Mapped[Optional[float]] = mapped_column(Float, comment="结果数据大小 (MB)")
    manually_stopped: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否被手动停止")
    # TaskRun 增加 node_id
    node_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cp_nodes.id"))

    node: Mapped["Node"] = relationship("Node")
    # 关联到主任务
    task: Mapped["Task"] = relationship("Task", back_populates="runs")