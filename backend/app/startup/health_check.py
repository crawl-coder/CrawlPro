# /backend/app/startup/health_check.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.startup.dependencies import (
    get_db,
    verify_healthcheck_token,
    get_scheduler_status
)

router = APIRouter()

@router.get("/", include_in_schema=False)
def read_root():
    return {"message": "Welcome to CrawlPro API", "status": "healthy"}

@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    scheduler_status: dict = Depends(get_scheduler_status),
    _: None = Depends(verify_healthcheck_token)  # 可选认证
):
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": scheduler_status
    }