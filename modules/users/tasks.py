"""Users module Celery tasks — student profile embedding pipeline."""
import logging

from core.celery_config import celery_app
from core.database import get_sync_db

logger = logging.getLogger(__name__)

_DIM_TEMPLATES = {
    "dim_sleep":        lambda p: f"sleep schedule: {p.sleep_schedule or 'unspecified'}",
    "dim_study":        lambda p: f"study habits: {p.study_habits or 'unspecified'}",
    "dim_cleanliness":  lambda p: f"cleanliness preference: {p.cleanliness or 'unspecified'}",
    "dim_guests":       lambda p: f"guests policy: {p.guests or 'unspecified'}",
    "dim_budget":       lambda p: (
        f"budget: {p.budget_min or 'unspecified'}–{p.budget_max or 'unspecified'} USD/month"
    ),
}


@celery_app.task(
    name="modules.users.tasks.embed_profile",
    bind=True,
    queue="nestai:low",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=90,
)
def embed_profile(self, user_id: int) -> None:
    from sqlalchemy import select, text

    from core.embeddings import embed_batch
    from modules.users.models import StudentProfile

    # Step 1: read profile — close session before slow inference
    all_texts = None
    with get_sync_db() as db:
        profile = db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        ).scalar_one_or_none()

        if profile is None:
            logger.info("embed_profile: no profile for user %s, skipping", user_id)
            return

        full_text = (
            f"sleep schedule: {profile.sleep_schedule or 'unspecified'}, "
            f"study habits: {profile.study_habits or 'unspecified'}, "
            f"cleanliness: {profile.cleanliness or 'unspecified'}, "
            f"guests: {profile.guests or 'unspecified'}, "
            f"language: {profile.language or 'unspecified'}, "
            f"budget: {profile.budget_min or 0}–{profile.budget_max or 0} USD/month"
        )
        dim_texts = [fn(profile) for fn in _DIM_TEMPLATES.values()]
        all_texts = [full_text] + dim_texts

    # Step 2: embed — no DB connection held during CPU inference
    vectors = embed_batch(all_texts)
    full_vec, *dim_vecs = vectors

    # Step 3: write all 6 vectors in a fresh session
    dim_keys = list(_DIM_TEMPLATES.keys())
    set_clauses = ", ".join(
        ["embedding = :embedding"] + [f"{k} = :{k}" for k in dim_keys]
    )
    params = {"user_id": user_id, "embedding": str(full_vec)}
    for k, v in zip(dim_keys, dim_vecs, strict=True):
        params[k] = str(v)

    with get_sync_db() as db:
        db.execute(
            text(f"UPDATE student_profiles SET {set_clauses} WHERE user_id = :user_id"),
            params,
        )
    logger.info("embed_profile: user %s — 6 vectors written", user_id)


@celery_app.task(
    name="modules.users.tasks.update_preference_vector",
    bind=True,
    queue="nestai:medium",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
)
def update_preference_vector(self, user_id: int) -> None:
    embed_profile.apply(args=[user_id])
