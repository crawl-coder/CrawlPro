# /app/schemas/node.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.node import NodeStatus, NodeOS


class NodeBase(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    status: NodeStatus
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime


class NodeCreate(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    os: Optional[NodeOS] = None


class NodeUpdate(BaseModel):
    ip_address: Optional[str] = None
    os: Optional[NodeOS] = None


class NodeOut(NodeBase):
    id: int

    class Config:
        from_attributes = True  # Pydantic V2