# /backend/app/core/config.py
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic.networks import AnyHttpUrl


# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 指向 CrawlPro 目录


class Settings(BaseSettings):
    """
    CrawlPro 应用配置类
    所有配置优先从 .env 文件加载，其次使用默认值
    """

    # ==================== API 配置 ====================
    API_V1_STR: str = Field("/api/v1", description="API 版本前缀")

    # 跨域配置：允许的前端域名
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[
            "http://localhost:8080",
            "http://localhost:5173",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:5173",
        ],
        description="允许的前端源（CORS）"
    )

    # ==================== 安全与认证 ====================
    SECRET_KEY: str = Field(
        "a_very_secret_key_change_in_production",
        description="JWT 签名密钥，生产环境必须更换"
    )
    ALGORITHM: str = Field("HS256", description="JWT 加密算法")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        60 * 24 * 7,  # 7天
        description="Token 过期时间（分钟）"
    )
    HEALTHCHECK_TOKEN: Optional[str] = 'oTjRedKlugSZ_qLTALHp5cM46u9j17EwwxQw982yHWA'

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = Field(
        "mysql+mysqldb://root:oscar&0503@localhost:3306/crawl_pro?charset=utf8mb4",
        description="MySQL 8 数据库连接地址"
    )
    SQLALCHEMY_DATABASE_URL: str = Field(
        "mysql+asyncmy://root:oscar&0503@localhost:3306/crawl_pro?charset=utf8mb4",
        description="MySQL 8 数据库连接地址(异步)"
    )

    # 同步连接（用于 Alembic 迁移）
    DATABASE_SYNC_URL: Optional[str] = Field(
        None,
        description="同步数据库连接（如 'mysql://...'），留空则自动转换"
    )

    # ==================== Redis & Celery 配置 ====================
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        description="Redis 地址（用于缓存、状态）"
    )

    CELERY_BROKER_URL: str = Field(
        "redis://localhost:6379/1",
        description="Celery 消息代理（Broker）"
    )

    CELERY_RESULT_BACKEND: str = Field(
        "redis://localhost:6379/2",
        description="Celery 结果后端"
    )

    # ==================== 存储路径配置 ====================
    # 项目根目录
    PROJECT_ROOT: str = Field(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        description="项目根路径"
    )

    # 上传的爬虫项目存储目录
    PROJECTS_DIR: str = str(BASE_DIR / "uploaded_projects")

    # 日志目录
    LOGS_DIR: str = Field(
        "logs",
        description="日志文件存储目录"
    )
    LOG_LEVEL: str = Field(
        "INFO",
        description="日志级别：DEBUG/INFO/WARNING/ERROR"
    )

    # 临时文件目录
    TEMP_DIR: str = Field(
        "tmp",
        description="临时文件目录"
    )

    # ==================== 服务配置 ====================
    SERVER_HOST: str = Field("0.0.0.0", description="服务监听地址")
    SERVER_PORT: int = Field(8000, description="服务监听端口")
    DEBUG: bool = Field(False, description="是否开启调试模式")

    # ==================== 调度器配置 ====================
    SCHEDULER_ENABLED: bool = Field(True, description="是否启用 APScheduler")
    SCHEDULER_JOB_STORE: str = Field("redis", description="调度器任务存储类型：'redis' 或 'sqlalchemy'")

    # ==================== 节点心跳 ====================
    NODE_HEARTBEAT_TTL: int = 60  # 心跳 TTL（秒）
    NODE_TIMEOUT_SECONDS: int = 120  # 超时判定时间

    # CrawlPro 主服务地址（Worker 用于反向注册）
    CRAWL_PRO_API_URL: str = "http://localhost:8000"
    TIMEZONE: str = "Asia/Shanghai"
    NODE_HEARTBEAT_CHECK_INTERVAL: int = 30
    # 用于加密 Git Token 的密钥
    # 请使用 `Fernet.generate_key()` 生成一个，并妥善保管
    ENCRYPTION_KEY: str = "8_mSLW_XAA62wk_Wxaj_5LSFKI5Tc2JPmwXM3Bfe-vI="

    WORKER_VERSION: str = Field("1.0.0", description="Worker 版本")
    WORKER_TAGS: str = Field("", description="Worker 标签，如 gpu,proxy")
    WORKER_CONCURRENCY: int = Field(4, description="Worker 最大并发数")
    WORKER_MEMORY_GB: Optional[float] = Field(None, description="Worker 内存大小（GB）")

    # ==================== 初始化处理 ====================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True  # 环境变量区分大小写

    @property
    def projects_full_path(self) -> str:
        """返回项目存储的绝对路径"""
        if os.path.isabs(self.PROJECTS_DIR):
            return self.PROJECTS_DIR
        return os.path.join(self.PROJECT_ROOT, self.PROJECTS_DIR)

    @property
    def logs_full_path(self) -> str:
        """返回日志目录的绝对路径"""
        if os.path.isabs(self.LOGS_DIR):
            return self.LOGS_DIR
        return os.path.join(self.PROJECT_ROOT, self.LOGS_DIR)

    @property
    def temp_full_path(self) -> str:
        """返回临时目录的绝对路径"""
        if os.path.isabs(self.TEMP_DIR):
            return self.TEMP_DIR
        return os.path.join(self.PROJECT_ROOT, self.TEMP_DIR)

    def ensure_directories(self):
        """创建必要的目录"""
        for path in [self.projects_full_path, self.logs_full_path, self.temp_full_path]:
            os.makedirs(path, exist_ok=True)


# 创建全局配置实例
settings = Settings()

# 启动时创建目录
settings.ensure_directories()