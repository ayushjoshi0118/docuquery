from celery import Celery
from docuquery.config import settings

celery_app = Celery(
    "docuquery_worker",
    broker=settings.get_celery_broker(),
    backend=settings.get_celery_backend(),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry=False,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=2.0,
    redis_socket_timeout=2.0,
    redis_socket_connect_timeout=2.0,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["docuquery.worker"])
