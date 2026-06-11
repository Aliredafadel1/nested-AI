from celery import Celery
from celery.schedules import crontab

import core.embeddings  # noqa: F401 — registers worker_process_init signal before fork
from core.config import settings

celery_app = Celery(
    "nestai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "modules.housing.tasks",
        "modules.users.tasks",
        "modules.fraud.tasks",
        "modules.contracts.tasks",
        "modules.agent.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Beirut",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,

    # 4 queues
    task_queues={
        "nestai:high":   {"exchange": "nestai", "routing_key": "high"},
        "nestai:medium": {"exchange": "nestai", "routing_key": "medium"},
        "nestai:low":    {"exchange": "nestai", "routing_key": "low"},
        "nestai:dead":   {"exchange": "nestai", "routing_key": "dead"},
    },
    task_default_queue="nestai:medium",

    # Task routing
    task_routes={
        "modules.housing.tasks.embed_listing":               {"queue": "nestai:low"},
        "modules.housing.tasks.batch_embed_seed_data":       {"queue": "nestai:low"},
        "modules.users.tasks.embed_profile":                 {"queue": "nestai:low"},
        "modules.users.tasks.update_preference_vector":      {"queue": "nestai:medium"},
        "modules.fraud.tasks.run_fraud_check":               {"queue": "nestai:medium"},
        "modules.contracts.tasks.analyze_contract_async":    {"queue": "nestai:high"},
        "modules.agent.tasks.index_rag_chunk":               {"queue": "nestai:low"},
        "modules.agent.tasks.seed_rag_embeddings":           {"queue": "nestai:low"},
    },

    # Beat scheduled tasks
    beat_schedule={
        "batch-embed-new-listings": {
            "task": "modules.housing.tasks.batch_embed_seed_data",
            "schedule": crontab(minute="*/10"),
        },
    },
)
