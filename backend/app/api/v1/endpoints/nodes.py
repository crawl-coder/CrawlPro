# /backend/app/api/v1/endpoints/nodes.py

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import deps
from app import models, schemas
from app.crud import node as crud_node

router = APIRouter()


# --- 🔐 私有接口：需要登录 ---
@router.get("/", response_model=List[schemas.NodeOut])
def read_nodes(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)  # ✅ 正确：前端用户查看
):
    return crud_node.get_multi(db, skip=skip, limit=limit)


@router.get("/{node_id}", response_model=schemas.NodeOut)
def read_node(
    *,
    node_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    db_node = crud_node.get(db, id=node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")
    return db_node


# --- 🌐 公开接口：Worker 自动上报，无需认证 ---
@router.post("/heartbeat", response_model=schemas.NodeOut)
def node_heartbeat(
    *,
    hostname: str = Form(...),
    ip: str = Form(...),
    db: Session = Depends(deps.get_db)
    # ❌ 不要加 current_user！Worker 没有 Token
):
    """
    Worker 定期上报心跳，无需认证
    """
    try:
        db_node = crud_node.register_or_update(db, hostname=hostname, ip_address=ip)
        return db_node
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register node: {str(e)}")


# --- 🔐 管理员接口 ---
@router.post("/{node_id}/offline")
def mark_node_offline(
    *,
    node_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser)  # ✅ 只有 superuser 能操作
):
    db_node = crud_node.get(db, id=node_id)
    if not db_node:
        raise HTTPException(status_code=404, detail="Node not found")

    crud_node.mark_offline(db, hostname=db_node.hostname)
    return {"success": True, "node_id": node_id, "status": "OFFLINE"}