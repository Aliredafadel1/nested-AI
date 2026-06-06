# NestAI

Lebanon-specific AI student housing platform. Modular monolith (10 bounded domain modules) + React frontend.

## CRITICAL: Module Boundaries — YOU MUST NOT VIOLATE

Each module owns its code and its DB tables exclusively. **Never import `modules/<X>/repository.py` from another module.** Cross-module calls go through `modules/<X>/service.py` only.

| Module | Path | Owned tables |
|--------|------|--------------|
| users | modules/users/ | users, student_profiles, landlord_profiles |
| housing | modules/housing/ | listings, listing_photos, listing_verifications, saved_listings, universities |
| roommate | modules/roommate/ | roommate_requests |
| agent | modules/agent/ | agent_sessions, student_memory, rag_chunks |
| fraud | modules/fraud/ | fraud_reports |
| contracts | modules/contracts/ | contracts |
| area_intel | modules/area_intel/ | neighborhoods |
| estimator | modules/estimator/ | cost_estimates |
| notifications | modules/notifications/ | notifications |
| reputation | modules/reputation/ | landlord_reviews |

## Commands

```bash
# Start all 13 services (add --profile init on first run to create MinIO buckets)
docker compose -f docker/docker-compose.yml up -d

# Apply DB schema (idempotent)
docker compose exec db psql -U nestai -d nestai -f /migrations/init.sql

# Run tests — always by file, not full suite
docker compose exec api pytest tests/test_api_listings.py -v
docker compose exec api pytest tests/test_agent_flow.py -v
docker compose exec api pytest tests/test_embeddings.py -v

# Spec validation — MUST pass before every commit
docker compose --profile spec run spec-validator

# Health check
curl http://localhost:8000/health

# Tail logs
docker compose logs api --tail=50 --follow

# Celery monitoring dashboard
docker compose --profile monitoring up flower   # → localhost:5555
```

## LLM Routing — IMPORTANT

All LLM calls go through `core/llm_router.py`. Never call OpenAI or Anthropic SDKs directly anywhere else.

| Tier | Model | Assign to |
|------|-------|-----------|
| free | BGE-M3 (local) | embed_listing, embed_profile, embed_query, embed_rag_chunk |
| cheap | GPT-4o mini | parse_intent, summarize_*, classify_fraud_text, explain_compatibility |
| powerful | Claude Sonnet | analyze_contract, agent_compare_explain, ocr_analyze_contract, validate_coherence |

Fallback chain: Claude Sonnet → GPT-4o → GPT-4o mini → stale Redis cache → graceful user-facing message. Never let the chain break silently.

## Security — Never Negotiate These

- JWT access tokens: React memory **only** — never `localStorage` (XSS risk).
- Refresh tokens: HttpOnly cookie + hashed in Redis. Rotate (issue new, delete old) on every use.
- File uploads: validate magic bytes via `core/storage.py` before writing to MinIO. Never trust `Content-Type`.
- LLM inputs: run through prompt injection sanitizer in `core/security.py` before every LLM call.
- Passwords: bcrypt work factor 12. Never log or store plaintext.
- Presigned URLs for private files: ≤15-minute expiry.

## Embeddings

BGE-M3 loads **once** at Celery worker startup via the `worker_init` signal in `core/embeddings.py`. Never load it per-request. All vectors are 1024-dim.

## Redis Keys

Never write raw key strings. Always use `RedisKeys.<method>()` from `core/redis.py`. 16 key patterns are defined there.

## No WebSockets

Real-time is SSE + Redis pub/sub only. Do not introduce WebSocket dependencies.

## Module Folder Structure

Every module follows this exact layout:

```
modules/<name>/
  router.py      # FastAPI APIRouter — no business logic
  service.py     # Business logic + the only cross-module interface
  repository.py  # DB queries — never imported outside this module
  models.py      # SQLAlchemy ORM models
  schemas.py     # Pydantic request/response schemas
```

## Testing Rules

- No database mocks — tests hit real containerized PostgreSQL.
- Agent tests cover the full 6-node LangGraph graph.
- After any agent change: `pytest tests/test_agent_flow.py`
- After any listing/housing change: `pytest tests/test_api_listings.py`

## Specs

- Module YAML contracts: `specs/all_modules.yaml` (validated by spec-validator service).
- Feature specs (SDD): `specs/<feature-id>/spec.md` → `plan.md` → `tasks.md`.
- Any new route or schema change must update `specs/all_modules.yaml` before merging.

Use `/nest-specify`, `/nest-plan`, `/nest-tasks`, `/nest-implement` skills for the SDD workflow.

## Environment

Local dev: copy `.env.dev` → `.env`. Never commit `.env.prod`. Required vars: `DATABASE_URL`, `REDIS_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.

## Compaction

When compacting, always preserve: current module being worked on, list of modified files, any failing test names, migration state (applied or not), and active LLM tier decisions.

<!-- SPECKIT START -->
Constitution: @.specify/memory/constitution.md
Phase specs (do not plan a phase until /speckit-clarify has run on its spec):
- Phase 1  Foundation:           @specs/001-foundation/spec.md
- Phase 2a Embeddings+Roommate:  @specs/002a-embeddings-roommate/spec.md
- Phase 2b Agent+Fraud+Contracts:@specs/002b-agent-fraud-contracts/spec.md
- Phase 3  Frontend:             @specs/003-frontend/spec.md
- Phase 4  Launch:               @specs/004-launch/spec.md
SDD workflow per phase: /speckit-clarify → /nest-plan → /nest-tasks → /nest-implement
<!-- SPECKIT END -->
