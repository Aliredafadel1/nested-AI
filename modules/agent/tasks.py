import logging

from core.celery_config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="modules.agent.tasks.index_rag_chunk",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    time_limit=60,
)
def index_rag_chunk(chunk_id: int) -> None:
    """Embed a rag_chunk row with BGE-M3 and store the vector."""
    import asyncio

    from core.config import settings

    async def _run():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from core.embeddings import embed_text

        engine = create_async_engine(settings.DATABASE_URL)
        async with AsyncSession(engine) as db:
            result = await db.execute(
                text("SELECT chunk_text FROM rag_chunks WHERE id = :id"),
                {"id": chunk_id},
            )
            row = result.fetchone()
            if not row:
                return

            vector = embed_text(row[0])
            await db.execute(
                text("UPDATE rag_chunks SET embedding = CAST(:vec AS vector) WHERE id = :id"),
                {"vec": str(vector), "id": chunk_id},
            )
            await db.commit()
        await engine.dispose()

    asyncio.run(_run())
    logger.info("index_rag_chunk | embedded chunk_id=%s", chunk_id)


@celery_app.task(
    name="modules.agent.tasks.seed_rag_embeddings",
    time_limit=600,
)
def seed_rag_embeddings() -> None:
    """Embed all rag_chunks where embedding IS NULL. Run once after seed SQL."""
    import asyncio

    from core.config import settings

    async def _run():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        engine = create_async_engine(settings.DATABASE_URL)
        async with AsyncSession(engine) as db:
            result = await db.execute(
                text("SELECT id FROM rag_chunks WHERE embedding IS NULL")
            )
            ids = [row[0] for row in result.fetchall()]

        await engine.dispose()
        logger.info("seed_rag_embeddings | found %s unembedded chunks", len(ids))
        for chunk_id in ids:
            index_rag_chunk.delay(chunk_id)

    asyncio.run(_run())
