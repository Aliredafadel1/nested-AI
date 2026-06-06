---
name: nest-tasks
description: Break a NestAI feature plan into ordered, phase-gated implementation tasks.
disable-model-invocation: true
---
Generate tasks for: $ARGUMENTS

Steps:

1. Read `specs/<feature>/plan.md` and `specs/<feature>/spec.md`.
2. Produce `specs/<feature>/tasks.md` with tasks organized into these phases:

   **Phase 1 — DB / Migration**
   - SQL changes to `migrations/init.sql`
   - Verify: `docker compose exec db psql -U nestai -d nestai -f /migrations/init.sql`

   **Phase 2 — Core changes** (only if needed)
   - `core/llm_router.py` — add new task names to TASK_TIERS
   - `core/redis.py` — add new RedisKeys methods
   - `core/storage.py` — add new bucket if needed

   **Phase 3 — Module backend** (for each affected module)
   - models.py → repository.py → service.py → schemas.py → router.py
   - Register router in `app/main.py` if new module
   - Verify: `curl http://localhost:8000/health`

   **Phase 4 — Celery tasks** (only if async processing needed)
   - Add task to `tasks/` and register in `core/celery_config.py`
   - Verify: `docker compose logs worker-high --tail=20`

   **Phase 5 — Frontend** (React components)
   - Order: API hook → component → route → integration with existing pages
   - Verify: start dev server and test in browser

   **Phase 6 — Tests**
   - Update or add to the relevant test file
   - Verify: `docker compose exec api pytest tests/<file> -v` — all pass

   **Phase 7 — Spec validation**
   - Update `specs/all_modules.yaml` to match implementation
   - Verify: `docker compose --profile spec run spec-validator` — exits 0

3. Mark parallel-safe tasks with `[P]`.
4. Each task must include: exact file path, what changes, and its verification command.
5. End tasks.md with: *"Final gate: `docker compose --profile spec run spec-validator && docker compose exec api pytest tests/ -v`"*
