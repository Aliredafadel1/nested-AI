# Research: Phase 2a — Embeddings + Roommate Matching

## BGE-M3 via sentence-transformers

**Decision**: Use `SentenceTransformer("BAAI/bge-m3")` from the `sentence-transformers` library.

**Rationale**: Already in `requirements.txt`. `encode()` returns numpy arrays, normalise with `normalize_embeddings=True` to get unit vectors — cosine similarity then equals dot product. BGE-M3 natively handles Arabic, French, and English — no preprocessing needed.

**Worker init pattern**:
```python
from celery.signals import worker_process_init

@worker_process_init.connect
def load_model(**kwargs):
    from core.embeddings import _load_model
    _load_model()
```
`_load_model()` sets a module-level `_model` variable. Subsequent calls to `embed_text()` use it without reloading.

**Model cache**: HuggingFace caches to `~/.cache/huggingface/hub/` by default. In Docker, the `worker-low` service mounts `bge_model_cache:/root/.cache/huggingface` — weights persist across container restarts.

---

## Celery Task Placement in Modular Monolith

**Decision**: `modules/housing/tasks.py` and `modules/users/tasks.py`.

**Rationale**: Constitution forbids cross-module repository imports. Placing tasks inside each module's directory keeps ownership clear. Tasks call their own module's `service.py` (or `repository.py` for simple DB writes that don't need business logic) — this is allowed since tasks are part of the same module.

**Alternative rejected**: A top-level `tasks/embed.py` that imports from both housing and users repositories would violate the module boundary rule.

---

## Redis Embed Cache Key

**Decision**: `RedisKeys.embed_cache(text_hash)` → `embed:{sha256_hex[:16]}` with 48h TTL.

**Rationale**: `sha256` of the input string is deterministic and collision-resistant for our corpus size. Truncating to 16 hex chars gives 64-bit collision space — sufficient. `RedisKeys` already has 16 patterns; we add one more.

---

## Distributed Lock for embed_listing

**Decision**: Redis SET NX with 30s TTL on key `lock:embed:{listing_id}`.

**Rationale**: Without a lock, two simultaneous creates (or a create + update race) could double-queue the same listing's embed task. The lock ensures only one task writes the vector at a time. 30s is conservative — BGE-M3 inference on a 300-token listing takes <2s on CPU.

---

## Roommate Match Query Strategy

**Decision**: Single SQL statement with 5 pgvector `<=>` cosine distance operators.

**Rationale**: FR-006 requires "5 separate pgvector cosine similarity queries (one per dim_* column)". A single SQL query with 5 `<=>` operators satisfies the spirit (one cosine op per dimension, computed in pgvector not Python) while avoiding 5 round-trips. This is more efficient and equally correct.

**Query shape**:
```sql
SELECT
    sp.user_id,
    ROUND(((1 - (dim_sleep      <=> :sv_sleep))
         + (1 - (dim_study      <=> :sv_study))
         + (1 - (dim_cleanliness<=> :sv_clean))
         + (1 - (dim_guests     <=> :sv_guests))
         + (1 - (dim_budget     <=> :sv_budget))) / 5.0, 4) AS score,
    (1 - (dim_sleep       <=> :sv_sleep))       AS sleep,
    (1 - (dim_study       <=> :sv_study))       AS study,
    (1 - (dim_cleanliness <=> :sv_clean))       AS cleanliness,
    (1 - (dim_guests      <=> :sv_guests))      AS guests,
    (1 - (dim_budget      <=> :sv_budget))      AS budget
FROM student_profiles sp
WHERE sp.user_id != :current_user_id
  AND sp.dim_sleep IS NOT NULL
ORDER BY score DESC
LIMIT 20;
```
Cosine similarity = 1 − cosine distance. pgvector `<=>` returns distance (0=identical, 2=opposite).

---

## 5 Dimension Sub-Embedding Text Templates

Confirmed from clarification:

| Dimension  | Text template                                  |
|------------|------------------------------------------------|
| sleep      | `"sleep schedule: {sleep_schedule}"`           |
| study      | `"study habits: {study_habits}"`               |
| cleanliness| `"cleanliness preference: {cleanliness}"`      |
| guests     | `"guests policy: {guests}"`                    |
| budget     | `"budget: {budget_min}–{budget_max} USD/month"`|

Null field fallback: `"unspecified"` — e.g. `"sleep schedule: unspecified"`.

---

## Migration Strategy

**Decision**: New file `migrations/002a_add_profile_dim_vectors.sql`, idempotent via `ADD COLUMN IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.

**Rationale**: Keeps Phase 1 migration (`init.sql`) untouched. Phase 2a migration runs after Phase 1 is confirmed working. Re-running is safe.
