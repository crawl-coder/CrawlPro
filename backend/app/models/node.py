# /backend/app/models/node.py

from typing import Optional
from enum import Enum as PyEnum  # ✅ Python 枚举
from sqlalchemy import Integer, String, DateTime, func, Enum as SqlEnum, Float  # ✅ SQL 列类型
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class NodeStatus(str, PyEnum):  # 使用 PyEnum（Python Enum）
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Node(Base):
    __tablename__ = "cp_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[NodeStatus] = mapped_column(
        SqlEnum(NodeStatus, name="node_status_enum"),
        default=NodeStatus.OFFLINE,
        nullable=False
    )
    last_heartbeat: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    registered_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # ✅ 新增字段
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, comment="CPU 核心数")
    memory_gb: Mapped[Optional[float]] = mapped_column(Float, comment="内存大小（GB）")
    disk_gb: Mapped[Optional[float]] = mapped_column(Float, comment="磁盘大小（GB）")
    version: Mapped[Optional[str]] = mapped_column(String(20), comment="Worker 版本")
    tags: Mapped[Optional[str]] = mapped_column(String(100), comment="节点标签，如 gpu,proxy")  # 可改为 JSON
    max_concurrency: Mapped[int] = mapped_column(Integer, default=4, comment="最大并发任务数")
    current_concurrency: Mapped[int] = mapped_column(Integer, default=0, comment="当前运行任务数")