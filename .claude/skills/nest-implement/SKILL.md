---
name: nest-implement
description: Implement a NestAI feature phase by phase from its tasks.md, running verification after each phase.
disable-model-invocation: true
---
Implement: $ARGUMENTS

Steps:

1. Read `specs/<feature>/tasks.md`. If $ARGUMENTS is blank, find the most recently modified tasks file.
2. Read `specs/<feature>/plan.md` and `specs/<feature>/spec.md` for full context.
3. Read `CLAUDE.md` for module boundary rules and security invariants — enforce them throughout.

4. Execute each phase in order. After each phase, run its verification command and fix failures before proceeding.

5. Checkpoints:
   - After Phase 3 (backend complete): `docker compose exec api pytest tests/test_api_listings.py -v`
   - After Phase 6 (tests): `docker compose exec api pytest tests/ -v`
   - After Phase 7 (spec): `docker compose --profile spec run spec-validator`

6. If spec validation fails: update `specs/all_modules.yaml` to match the implementation, then re-run.

7. Security check before finishing — confirm:
   - No direct cross-module repository imports introduced
   - Any file upload path uses `core/storage.py` magic byte validation
   - Any LLM call goes through `core/llm_router.py`
   - New endpoints respect the authorization matrix from CLAUDE.md

8. Report: files changed (with line counts), tests status, spec validation exit code.
