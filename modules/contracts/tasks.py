import hashlib
import json
import logging

from core.celery_config import celery_app

logger = logging.getLogger(__name__)

CONTRACT_CACHE_TTL = 24 * 3600   # cached analyses live 24 h
MAX_CLAUSES_FOR_DEEP = 12        # Sonnet only sees up to this many flagged clauses


@celery_app.task(
    name="modules.contracts.tasks.analyze_contract_async",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    time_limit=300,
)
def analyze_contract_async(contract_id: int) -> None:
    """Analyze a PDF contract asynchronously. Triggered after upload."""
    import asyncio
    from core.config import settings

    logger.info("analyze_contract_async | contract_id=%s", contract_id)

    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        engine = create_async_engine(settings.DATABASE_URL)
        async with AsyncSession(engine) as db:
            from modules.contracts.repository import ContractsRepository
            repo = ContractsRepository(db)

            contract = await repo.get_by_id(contract_id)
            if not contract:
                logger.warning("analyze_contract_async | contract %s not found", contract_id)
                return

            # Download PDF from MinIO
            from core.storage import get_minio_client, Bucket
            import io
            client = get_minio_client()
            try:
                response = client.get_object(Bucket.CONTRACTS.value, contract.minio_key)
                file_bytes = response.read()
                response.close()
                response.release_conn()
            except Exception as e:
                logger.error("analyze_contract_async | MinIO download failed: %s", e)
                await repo.update_status(contract_id, "failed")
                return

            # Try PyMuPDF text extraction
            ocr_used = False
            text = ""
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                text = " ".join(page.get_text() for page in doc)
                doc.close()
            except Exception as e:
                logger.warning("analyze_contract_async | PyMuPDF failed: %s", e)

            # OCR fallback if text is empty
            if not text.strip():
                ocr_used = True
                await repo.update_status(contract_id, "ocr_running")
                text = await _ocr_pdf(file_bytes)

            if not text.strip():
                await repo.update_status(contract_id, "failed")
                return

            await repo.update_status(contract_id, "analyzing")
            from core.llm_router import call_llm
            import redis as redis_sync
            from core.config import settings

            # ── Tokenomics optimisation 1: hash cache ────────────────────────
            # If this exact contract text was analyzed before, return cached result.
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:32]
            cache_key = f"contract_analysis:{text_hash}"
            r = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                cached_raw = r.get(cache_key)
            finally:
                r.close()

            if cached_raw:
                logger.info("analyze_contract_async | cache hit for hash %s", text_hash)
                analysis = json.loads(cached_raw)
                await repo.update_analysis(contract_id, ocr_used, analysis, status="complete")
                await engine.dispose()
                return

            # ── Tokenomics optimisation 2: two-pass analysis ─────────────────
            # Pass 1 (cheap — GPT-4o mini): scan all clauses, flag which are risky.
            screen_prompt = (
                "You are a Lebanese lease contract screener. Read the contract below and return "
                "a JSON array of objects, each with:\n"
                "  'clause_text': exact quote (max 300 chars)\n"
                "  'suspicion': 'high', 'medium', or 'low'\n"
                "Flag: hidden fees, unfair eviction, ambiguous renewal, missing tenant rights, "
                "electricity/generator responsibilities, illegal penalty clauses.\n"
                "Return ONLY the JSON array — no prose.\n\n"
                f"CONTRACT:\n{text[:12000]}"
            )
            raw_screen = call_llm("parse_intent", screen_prompt, max_tokens=1500)
            flagged_clauses: list[dict] = []
            try:
                parsed_screen = json.loads(raw_screen)
                if isinstance(parsed_screen, list):
                    flagged_clauses = [
                        c for c in parsed_screen
                        if isinstance(c, dict) and c.get("suspicion") in ("high", "medium")
                    ][:MAX_CLAUSES_FOR_DEEP]
            except Exception:
                # Screening failed — fall back to full single-pass below
                flagged_clauses = []

            # Pass 2 (powerful — Claude Sonnet): deep-dive flagged clauses only.
            if flagged_clauses:
                clauses_text = json.dumps(flagged_clauses, ensure_ascii=False)
                task_name = "ocr_analyze_contract" if ocr_used else "analyze_contract"
                deep_prompt = (
                    "You are a Lebanese tenant rights expert. The following clauses have been "
                    "pre-screened as potentially risky in a rental lease agreement. "
                    "For each clause provide a plain-language explanation of the risk and its severity.\n"
                    "Return a JSON object with key 'risk_items', each item having:\n"
                    "  'level': 'high', 'medium', or 'low'\n"
                    "  'clause_text': the exact clause (as provided)\n"
                    "  'explanation': clear explanation for a Lebanese student tenant\n\n"
                    f"FLAGGED CLAUSES:\n{clauses_text}"
                )
                raw_analysis = call_llm(task_name, deep_prompt, max_tokens=2000)
            else:
                # Fallback: no flags from screener OR screener failed — full single-pass
                task_name = "ocr_analyze_contract" if ocr_used else "analyze_contract"
                full_prompt = (
                    "Analyze this Lebanese rental lease contract and identify risk items for the tenant. "
                    "Return a JSON object with key 'risk_items', each with: "
                    "'level' (high/medium/low), 'clause_text' (exact quote), "
                    "'explanation' (plain-language for a Lebanese student).\n\n"
                    f"CONTRACT:\n{text[:8000]}"
                )
                raw_analysis = call_llm(task_name, full_prompt, max_tokens=2000)

            # Parse the deep-analysis response
            analysis = {"risk_items": []}
            try:
                parsed = json.loads(raw_analysis)
                if isinstance(parsed, dict) and "risk_items" in parsed:
                    items = parsed["risk_items"]
                    order = {"high": 0, "medium": 1, "low": 2}
                    items.sort(key=lambda x: order.get(x.get("level", "low"), 3))
                    analysis = {"risk_items": items}
            except Exception:
                analysis = {
                    "risk_items": [{
                        "level": "medium",
                        "clause_text": "See full analysis",
                        "explanation": str(raw_analysis)[:500],
                    }]
                }

            # Cache the result so identical re-uploads are free
            r2 = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                r2.setex(cache_key, CONTRACT_CACHE_TTL, json.dumps(analysis))
            finally:
                r2.close()

            logger.info(
                "analyze_contract_async | two-pass complete | flagged=%d clauses | contract_id=%s",
                len(flagged_clauses), contract_id,
            )
            await repo.update_analysis(contract_id, ocr_used, analysis, status="complete")

        await engine.dispose()
        logger.info("analyze_contract_async | completed for contract_id=%s", contract_id)

    asyncio.run(_run())


async def _ocr_pdf(file_bytes: bytes) -> str:
    """Convert PDF pages to images and run GPT-4o Vision OCR."""
    try:
        import fitz
        import base64
        from core.llm_router import _openai_client
        import os

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = []
        client = _openai_client()

        for page_num, page in enumerate(doc):
            if page_num >= 10:
                break
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode()

            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this lease contract page verbatim."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                }],
            )
            all_text.append(response.choices[0].message.content)

        doc.close()
        return "\n".join(all_text)
    except Exception as e:
        logger.error("_ocr_pdf | OCR failed: %s", e)
        return ""
