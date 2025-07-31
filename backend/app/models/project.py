from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey, Boolean, JSON,  Enum as SqlEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base_class import Base


class ProjectStatus(str, PyEnum):
    DEVELOPING = "DEVELOPING"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

class Project(Base):
    __tablename__ = "cp_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    package_path: Mapped[Optional[str]] = mapped_column(String(255), comment="爬虫部署包在服务器上的相对路径")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # ✅ 新增字段
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("cp_users.id"), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        SqlEnum(ProjectStatus, name="project_status_enum"),
        default=ProjectStatus.DEVELOPING
    )
    version: Mapped[Optional[str]] = mapped_column(String(20), default="1.0.0")
    entrypoint: Mapped[str] = mapped_column(String(100), default="run.py", comment="入口脚本")
    has_requirements: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否有 requirements.txt")
    env_template: Mapped[Optional[dict]] = mapped_column(JSON, comment="环境变量模板")

    # 关系
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")