---
name: nest-plan
description: Generate a technical implementation plan for a NestAI feature from its spec.md.
disable-model-invocation: true
---
Generate a technical plan for: $ARGUMENTS

**STOP — Clarify first.** Before writing any plan, check whether `/speckit-clarify` has been run for this spec:
- Look for a `## Clarifications` section in `specs/<feature>/spec.md`.
- If it does NOT exist, tell the user: *"Run `/speckit-clarify` on this spec before planning. Unresolved ambiguities in the spec become expensive mistakes in the plan."* Then stop.
- If it exists, proceed.

Steps:

1. Read `specs/<feature>/spec.md` (including the Clarifications section). If $ARGUMENTS is blank, find the most recently modified spec.
2. Read the service files for every affected module listed in the spec.
3. Read `core/llm_router.py` to see the TASK_TIERS dict before adding any new LLM task names.
4. Read `core/redis.py:RedisKeys` to see existing key patterns before adding new ones.

5. Produce `specs/<feature>/plan.md` covering:
   - **Architecture decisions**: which service interfaces to add or modify (no repository cross-imports)
   - **Database changes**: exact column additions with PostgreSQL types and constraints
   - **API contracts**: for each endpoint — method, path, auth role, request schema, response schema, error codes
   - **LLM routing**: tier (free/cheap/powerful) and exact task name string for any new LLM call
   - **Redis keys**: new entries needed in `RedisKeys`, including type and TTL
   - **Celery tasks**: queue (high/medium/low), timeout, retry policy if async processing is needed
   - **Module boundary check**: confirm no plan requires a repository import across modules
   - **Test plan**: which test file to update, what scenarios to cover (happy path + at least 2 edge cases)

6. Update `specs/all_modules.yaml` with any new endpoints or schema changes the plan introduces.

7. End with: *"Run `/nest-tasks` to generate the ordered task breakdown."*
