# /backend/app/main.py
from fastapi import FastAPI
from app.core.lifespan import lifespan
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.startup.middleware import setup_cors
from app.startup.health_check import router as health_router
from app.api.v1.api import api_router

# 初始化日志
setup_logging()

# 创建 FastAPI 应用
app = FastAPI(
    title="CrawlPro - 通用分布式任务调度平台",
    description="一个支持 Python、Shell、Node.js 等多种脚本的爬虫与任务管理系统",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# 配置中间件
setup_cors(app)

# 包含路由
app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_V1_STR)

# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1  # 开发时建议单worker
    )