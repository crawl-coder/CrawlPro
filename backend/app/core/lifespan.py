# /backend/app/core/lifespan.py
from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.services.scheduler import scheduler_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命周期管理"""
    logger.info("🚀 CrawlPro 正在启动...")

    # 数据库连接检查 - 现在可以使用同步 Session
    try:
        # 方法 1: 使用 SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()

        # 或者 方法 2: 直接使用 engine.connect()
        # with engine.connect() as conn:
        #     conn.execute(text("SELECT 1"))

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

    # 关闭引擎
    engine.dispose()
    logger.info("✅ 数据库引擎已关闭")