# /app/services/node_monitor.py
import time
from sqlalchemy.orm import Session
from app.crud import node
from app.core.config import settings


def start_node_monitor(db: Session, interval: int = 60):
    """定期检查节点心跳，超时标记为 OFFLINE"""
    while True:
        cutoff = time.time() - settings.NODE_TIMEOUT_SECONDS  # 如 120 秒
        # 查询 last_heartbeat < now - 120s 的节点
        # 执行标记为 OFFLINE
        time.sleep(interval)