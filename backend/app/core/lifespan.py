# /backend/app/core/lifespan.py
from loguru import logger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine
from app.services.scheduler import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    logger.info("🚀 CrawlPro 正在启动...")

    # 数据库连接检查
    try:
        with Session(engine) as db:
            db.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接正常")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise

    # 启动定时调度器
    try:
        scheduler_service.start()
        logger.info("✅ 定时任务调度器已启动")
    except Exception as e:
        logger.error(f"❌ 调度器启动失败: {e}")
        raise

    yield  # 应用运行中

    # 关闭时清理
    logger.info("🛑 CrawlPro 正在关闭...")
    try:
        scheduler_service.shutdown()
        logger.info("✅ 调度器已安全关闭")
    except Exception as e:
        logger.error(f"❌ 调度器关闭失败: {e}")