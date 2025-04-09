from celery import Celery
from app.core.config import settings

# Создание экземпляра Celery
celery_app = Celery(
    "doors_shop_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.product_tasks"]
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
)

if __name__ == "__main__":
    celery_app.start()