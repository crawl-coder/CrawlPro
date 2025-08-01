# /backend/app/tasks/worker_signals.py
import os
import socket
import platform
import requests
from loguru import logger
from celery.signals import worker_process_init, worker_shutdown, heartbeat_sent
from app.core.config import settings

# --- 获取本机信息 ---
def get_local_ip() -> str:
    """获取本机内网 IP 地址"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"  # 安全兜底

# --- 基础信息 ---
HOSTNAME = socket.gethostname()
LOCAL_IP = get_local_ip()
WORKER_OS = platform.system().upper()  # 'WINDOWS' or 'LINUX'
WORKER_OS_VERSION = platform.release()  # 更稳定的版本号
PYTHON_VERSION = platform.python_version()


# --- Redis 心跳键 ---
HEARTBEAT_KEY = f"nodes:heartbeat:{HOSTNAME}"
HEARTBEAT_TTL = getattr(settings, 'NODE_HEARTBEAT_TTL', 60)  # 默认 60 秒

# --- CrawlPro API 注册地址 ---
# ✅ 修复拼写错误：CRAWL_PRO_API_URL
REGISTER_URL = f"{settings.CRAWL_PRO_API_URL.rstrip('/')}/api/v1/nodes/heartbeat"

# --- 信号处理 ---

@worker_process_init.connect
def worker_process_init_handler(**kwargs):
    """
    在每个 Worker 子进程启动时触发
    上报节点信息到主服务
    """
    os.environ["OS_TYPE"] = WORKER_OS
    logger.info(f"Worker process initializing on {HOSTNAME} (IP: {LOCAL_IP}, OS: {WORKER_OS})")

    # 1. 向 Redis 上报心跳
    try:
        from redis import from_url
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
                "hostname": HOSTNAME,
                "ip": LOCAL_IP,
                "os": WORKER_OS,
                "os_version": WORKER_OS_VERSION,
                "python_version": PYTHON_VERSION,
                "version": getattr(settings, 'WORKER_VERSION', '1.0.0'),
                "cpu_cores": platform.processor(),  # 简单标识
                "memory_gb": getattr(settings, 'WORKER_MEMORY_GB', None),
                "tags": getattr(settings, 'WORKER_TAGS', ''),
                "max_concurrency": getattr(settings, 'WORKER_CONCURRENCY', 4)
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
        logger.debug(f"Heartbeat updated for {HOSTNAME}")
    except Exception as e:
        logger.warning(f"Heartbeat update failed: {e}")


@worker_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """
    Worker 关闭时清理资源
    """
    logger.info(f"Worker {HOSTNAME} is shutting down. Cleaning up...")

    # 1. 清理 Redis 心跳
    try:
        from redis import from_url
        redis_client = from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.delete(HEARTBEAT_KEY)
        logger.info(f"Heartbeat key deleted: {HEARTBEAT_KEY}")
    except Exception as e:
        logger.warning(f"Failed to delete heartbeat key: {e}")

    # 2. 可选：通知主服务节点离线（幂等）
    try:
        offline_url = f"{settings.CRAWL_PRO_API_URL.rstrip('/')}/api/v1/nodes/offline"
        requests.post(
            offline_url,
            data={"hostname": HOSTNAME},
            timeout=3
        )
        logger.info(f"Sent offline notification to {offline_url}")
    except Exception as e:
        logger.debug(f"Offline notification failed (ignored): {e}")