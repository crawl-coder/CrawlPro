# /app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 使用同步的 URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 创建同步引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    echo=False, # 生产环境设为 False
)

# 创建同步 Session 工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
