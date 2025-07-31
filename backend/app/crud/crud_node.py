# /app/crud/crud_node.py

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func
from app.crud.base import CRUDBase
from app.models.node import Node, NodeStatus
from app.schemas.node import NodeCreate, NodeUpdate


class CRUDNode(CRUDBase[Node, NodeCreate, NodeUpdate]):
    def get_by_hostname(self, db: Session, *, hostname: str) -> Optional[Node]:
        stmt = select(self.model).where(self.model.hostname == hostname)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    def register_or_update(self, db: Session, *, hostname: str, ip_address: str) -> Node:
        """注册或更新节点"""
        db_node = self.get_by_hostname(db, hostname=hostname)
        if not db_node:
            db_node = self.model(
                hostname=hostname,
                ip_address=ip_address,
                status=NodeStatus.ONLINE
            )
            db.add(db_node)
        else:
            db_node.ip_address = ip_address
            db_node.status = NodeStatus.ONLINE
            db_node.last_heartbeat = func.now()

        db.commit()
        db.refresh(db_node)
        return db_node

    def heartbeat(self, db: Session, *, hostname: str) -> bool:
        """节点心跳"""
        stmt = update(self.model).where(
            self.model.hostname == hostname
        ).values(
            status=NodeStatus.ONLINE,
            last_heartbeat=func.now()
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    def mark_offline(self, db: Session, *, hostname: str) -> None:
        """标记节点离线"""
        stmt = update(self.model).where(
            self.model.hostname == hostname
        ).values(
            status=NodeStatus.OFFLINE
        )
        db.execute(stmt)
        db.commit()


node = CRUDNode(Node)