# /backend/app/startup/dependencies.py
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine
from app.services.scheduler import scheduler_service
from fastapi import Depends, HTTPException, status
from app.core.config import settings
from typing import Generator, AsyncGenerator, Optional # 添加 AsyncGenerator

def get_db() -> Generator[Session, None, None]:
    """
    获取【同步】数据库会话的依赖项
    使用方式：db: Session = Depends(get_db)
    """
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def verify_healthcheck_token(token: Optional[str] = None):
    """
    健康检查的简单认证（可选）
    使用方式：Depends(verify_healthcheck_token)
    """
    if settings.HEALTHCHECK_TOKEN and token != settings.HEALTHCHECK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid healthcheck token"
        )

def get_scheduler_status() -> dict:
    """
    获取调度器状态的依赖项
    """
    return {
        "is_running": scheduler_service.is_running(),
        "jobs": scheduler_service.get_job_count()
    }