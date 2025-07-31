# /backend/app/core/logging_config.py

import sys
from loguru import logger


def setup_logging():
    """
    配置 Loguru，使其输出结构化的 JSON 日志。
    """
    # 1. 移除默认的处理器，以便我们完全控制
    logger.remove()

    # 2. 添加一个用于在开发时方便查看的、彩色的控制台输出
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # 3. 添加一个用于生成 JSON 格式日志文件的处理器
    #    `serialize=True` 是关键，它会将每条日志记录转换为 JSON 字符串。
    logger.add(
        "logs/crawlpro_{time}.log",
        level="INFO",
        rotation="10 MB",  # 每 10 MB 切割一个新文件
        retention="7 days",  # 保留最近 7 天的日志
        enqueue=True,  # 异步写入，避免阻塞主线程
        serialize=True  # <--- 这是实现结构化日志的核心！
    )

    # 4. 配置 Celery Worker 的日志记录器
    # (这部分将在 Celery Worker 启动时单独处理)

    logger.info("Logger setup complete.")