<!-- SYNC IMPACT REPORT
Version change: informal draft → 1.0.0
Modified principles: All formalized from prose to structured spec-kit format
Added sections: Governance, Lebanon Context, Quality Gates
Removed: none
Templates requiring updates: None — generic templates unchanged
Deferred TODOs: None
-->

# NestAI Constitution

## Core Principles

### I. Modular Boundaries (NON-NEGOTIABLE)

Each of the 10 domain modules owns its code and its database tables exclusively.
- A module's `repository.py` MUST NOT be imported by any other module.
- Cross-module data access MUST go through the owning module's `service.py`.
- New modules MUST follow the exact 5-file layout: `router.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`.
- Rationale: enforces clean separation, independent testability, and a safe microservice extraction path.

### II. Security-First (NON-NEGOTIABLE)

Security constraints are not optional and cannot be deferred to "later":
- JWT access tokens MUST be stored in React memory only — never `localStorage` (XSS risk).
- Refresh tokens MUST be HttpOnly cookie only, hashed in Redis, rotated on every use.
- Every file upload MUST validate magic bytes via `core/storage.py` before writing to MinIO. Content-Type MUST NOT be trusted.
- Every LLM input MUST pass through the prompt injection sanitizer in `core/security.py`.
- Passwords MUST use bcrypt work factor 12 and MUST never appear in logs or responses.
- Presigned URLs for private buckets MUST expire in ≤15 minutes.

### III. AI Cost Discipline

All LLM calls MUST be routed through `core/llm_router.py`. Direct SDK calls to OpenAI or Anthropic are forbidden outside of this file.
- Embedding tasks MUST use `paraphrase-multilingual-MiniLM-L12-v2` (local, free, 384-dim). The model MUST load once at Celery worker startup — never per-request.
- High-volume tasks (intent parsing, summarization, classification) MUST use GPT-4o mini (~$0.15/1M tokens).
- Deep reasoning tasks (contract analysis, multi-listing comparison, coherence validation) MUST use Claude Sonnet (~$3/1M tokens).
- Redis LLM cache (6-24h TTL by task type) MUST be checked before every LLM call.
- Target: ≥85% cost reduction vs. using GPT-4o for all tasks.
- Fallback chain MUST always resolve: Claude Sonnet → GPT-4o → GPT-4o mini → stale Redis cache → graceful user-facing message. Silent failures are forbidden.

### IV. Real Data in Tests

Integration tests MUST hit real containerized PostgreSQL and Redis. Database mocks are forbidden.
- The LangGraph agent MUST be tested through its full 6-node graph, not individual nodes in isolation.
- After any module change, the affected module's test file MUST pass before the PR is merged.
- `docker compose --profile spec run spec-validator` MUST exit 0 before every deploy.

### V. Spec-Before-Code (SDD Workflow)

No new feature or module change begins without a spec:
1. `/nest-specify <feature>` → `specs/<feature>/spec.md`
2. `/nest-plan` → `specs/<feature>/plan.md` + updates `specs/all_modules.yaml`
3. `/nest-tasks` → `specs/<feature>/tasks.md`
4. `/nest-implement` → phase-by-phase with verification gates
- Any new API route or schema change MUST update `specs/all_modules.yaml` before merging.

### VI. Lebanon-Aware by Default

Lebanon-specific context is a first-class concern, not a localization afterthought:
- Prices MUST be stored and displayed in USD (Lebanon's rental market operates in USD despite LBP).
- Electricity schedule and generator cost MUST be first-class attributes of neighborhood data — not optional notes.
- All text inputs and LLM prompts MUST be treated as potentially Arabic, French, or English. The multilingual MiniLM embedding model handles all three natively.
- Every user-facing error MUST be a human-readable, actionable message — never a blank screen or raw exception (users are often on mobile in low-connectivity environments).
- Graceful LLM degradation is mandatory: if all LLM providers fail, serve stale Redis cache and inform the user explicitly.

## Quality Gates

Every pull request MUST pass all of these before merge:

| Gate | Command | Threshold |
|------|---------|-----------|
| Tests | `docker compose exec api pytest tests/<changed-module>.py -v` | All pass |
| Spec validation | `docker compose --profile spec run spec-validator` | Exit 0 |
| No cross-module imports | Grep for `from modules.<X>.repository import` in other modules | Zero matches |
| No direct LLM SDK calls | Grep for `openai.` / `anthropic.` outside `core/llm_router.py` | Zero matches |
| Security review | Use the `security-reviewer` subagent on changed files | No critical findings |

## Lebanon Context Reference

- 10 Lebanese universities seeded with lat/lng for OSRM commute calculations.
- 8 Beirut neighbourhoods seeded with electricity hours, generator cost, internet quality, transport score, safety score, and student vibe score.
- 50 realistic seed listings in USD across those 8 neighbourhoods.
- OSRM routing is self-hosted and free — no Google Maps API cost.

## Governance

- This constitution supersedes all other guidelines and informal conventions.
- Amendments require: written rationale, version bump, and propagation check against all plan/spec/tasks templates.
- Version bump rules: MAJOR = principle removal or incompatible redefinition; MINOR = new principle or material expansion; PATCH = clarifications or wording.
- The "Constitution Check" gate in every `plan.md` MUST be completed before Phase 0 research begins.
- The constitution is reviewed at the end of every build sprint and amended if new constraints are discovered.
- Runtime guidance lives in `CLAUDE.md` (always loaded) and `specs/all_modules.yaml` (machine-validated contracts).

### Amendment Log

- **1.1.0** (2026-07-20): Principle III's embedding model was documented as BGE-M3 (1024-dim) but the shipped implementation (`core/embeddings.py`, `migrations/init.sql`) has always used `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) — discovered during a full-system test pass. Rather than force a re-embed migration, this amendment brings the constitution in line with the running system. MINOR bump: the principle (local, free, multilingual embeddings routed through the worker) is unchanged; only the specific model/dimension value is corrected.

**Version**: 1.1.0 | **Ratified**: 2026-06-05 | **Last Amended**: 2026-07-20
