# /app/crud/crud_node.py
import datetime
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

    def register_or_update(self, db, *, hostname: str, ip_address: str, os: str):
        node = self.get_by_hostname(db, hostname=hostname)
        if not node:
            node_in = NodeCreate(hostname=hostname, ip_address=ip_address, os=os)
            node = self.create(db, obj_in=node_in)
        else:
            node_update = NodeUpdate(ip_address=ip_address, os=os)
            node = self.update(db, db_obj=node, obj_in=node_update)
        node.status = "ONLINE"
        node.last_heartbeat = datetime.datetime.utcnow()
        db.add(node)
        db.commit()
        db.refresh(node)
        return node

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