# /backend/app/core/celery_app.py

from celery import Celery
from app.core.config import settings

# ✅ 使用标准命名 `celery`
celery = Celery(
    "CrawlPro",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.crawler_tasks',
        'app.tasks.worker_signals'
    ]
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=False,
)