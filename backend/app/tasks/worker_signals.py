# /backend/app/tasks/worker_signals.py

import socket
import logging
import requests
from celery.signals import heartbeat_sent, worker_process_init, worker_shutdown
from app.core.config import settings

# --- 配置日志 ---
logging.basicConfig(level=settings.LOG_LEVEL or "INFO")
logger = logging.getLogger(__name__)

# --- 获取本机信息 ---
def get_local_ip() -> str:
    """获取本机内网 IP 地址"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "unknown"

hostname = socket.gethostname()
local_ip = get_local_ip()

# --- Redis 心跳键 ---
HEARTBEAT_KEY = f"nodes:heartbeat:{hostname}"
HEARTBEAT_TTL = settings.NODE_HEARTBEAT_TTL or 60  # 秒

# --- CrawlPro API 注册地址 ---
REGISTER_URL = f"{settings.CRAWLPRO_API_URL.rstrip('/')}/api/v1/nodes/heartbeat"

# --- 信号处理 ---

@worker_process_init.connect
def worker_process_init_handler(**kwargs):
    """
    比 worker_ready 更可靠的初始化信号
    在每个 Worker 子进程启动时触发
    """
    logger.info(f"Worker process initializing on {hostname} (IP: {local_ip})")

    # 1. 向 Redis 上报心跳（用于快速检测）
    try:
        from redis import from_url, Redis
        redis_client = from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_TTL)
        logger.info(f"Heartbeat key set in Redis: {HEARTBEAT_KEY}")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}")

    # 2. 向 CrawlPro 主服务注册节点（HTTP）
    try:
        response = requests.post(
            REGISTER_URL,
            data={
                "hostname": hostname,
                "ip": local_ip
            },
            timeout=5
        )
        if response.status_code == 200:
            logger.info(f"Successfully registered to CrawlPro at {REGISTER_URL}")
        else:
            logger.error(f"Failed to register: {response.status_code} {response.text}")
    except requests.RequestException as e:
        logger.error(f"Failed to register to CrawlPro: {e}")


@heartbeat_sent.connect
def heartbeat_sent_handler(**kwargs):
    """
    Celery 内建心跳信号，定期触发
    用于维持 Redis 心跳键的存活
    """
    try:
        from redis import from_url
        redis_client = from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_TTL)
        logger.debug(f"Heartbeat updated for {hostname}")
    except Exception as e:
        logger.warning(f"Heartbeat update failed: {e}")


@worker_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """
    Worker 关闭时清理资源
    """
    logger.info(f"Worker {hostname} is shutting down. Cleaning up...")

    # 1. 清理 Redis 心跳
    try:
        from redis import from_url
        redis_client = from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.delete(HEARTBEAT_KEY)
        logger.info(f"Heartbeat key deleted: {HEARTBEAT_KEY}")
    except Exception as e:
        logger.warning(f"Failed to delete heartbeat key: {e}")

    # 2. 可选：通知主服务（幂等操作，失败也无妨）
    try:
        requests.post(
            f"{settings.CRAWLPRO_API_URL}/api/v1/nodes/offline",
            data={"hostname": hostname},
            timeout=3
        )
    except Exception:
        pass  # 无需阻塞退出