# /backend/app/models/node.py

from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, DateTime, func, Enum as SqlEnum, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class NodeStatus(str, PyEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class NodeOS(str, PyEnum):
    """
    节点操作系统类型
    """
    WINDOWS = "WINDOWS"
    LINUX = "LINUX"
    MACOS = "MACOS"
    UNKNOWN = "UNKNOWN"


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

    # ✅ 操作系统信息（用于区分 Windows/Linux）
    os: Mapped[NodeOS] = mapped_column(
        SqlEnum(NodeOS, name="node_os_enum"),
        default=NodeOS.UNKNOWN,
        nullable=False
    )
    os_version: Mapped[Optional[str]] = mapped_column(String(50), comment="操作系统版本，如 Windows 11, Ubuntu 20.04")

    # ✅ 硬件资源
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, comment="CPU 核心数")
    cpu_usage: Mapped[Optional[float]] = mapped_column(Float, comment="CPU 使用率 (%)")
    memory_gb: Mapped[Optional[float]] = mapped_column(Float, comment="内存大小（GB）")
    memory_usage: Mapped[Optional[float]] = mapped_column(Float, comment="内存使用量（GB）")
    disk_gb: Mapped[Optional[float]] = mapped_column(Float, comment="磁盘大小（GB）")
    disk_usage: Mapped[Optional[float]] = mapped_column(Float, comment="磁盘使用量（GB）")

    # ✅ 软件与版本
    version: Mapped[Optional[str]] = mapped_column(String(20), comment="Worker 版本")
    python_version: Mapped[Optional[str]] = mapped_column(String(20), comment="Python 版本")
    # 如果支持 Node.js/PHP 等，也可加

    # ✅ 标签与能力
    tags: Mapped[Optional[str]] = mapped_column(String(100), comment="节点标签，如 gpu,proxy,chrome")
    capabilities: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="节点能力（JSON 格式），如 {'gpu': true, 'browser': 'chrome'}"
    )  # 后续可改为 JSON 类型

    # ✅ 并发控制
    max_concurrency: Mapped[int] = mapped_column(Integer, default=4, comment="最大并发任务数")
    current_concurrency: Mapped[int] = mapped_column(Integer, default=0, comment="当前运行任务数")

    # ✅ 网络信息（可选）
    public_ip: Mapped[Optional[str]] = mapped_column(String(50), comment="公网 IP")
    agent_port: Mapped[Optional[int]] = mapped_column(Integer, comment="Worker 通信端口")