# Research: Phase 2a — Embeddings + Roommate Matching

## MiniLM via sentence-transformers

**Decision**: Use `SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")` from the `sentence-transformers` library. (2026-07-20: this spec originally called for `BAAI/bge-m3`; the shipped code has always used MiniLM instead — see spec.md's 2026-07-20 clarification. This section now documents what's actually running.)

**Rationale**: Already in `requirements.txt`. `encode()` returns numpy arrays, normalise with `normalize_embeddings=True` to get unit vectors — cosine similarity then equals dot product. The multilingual MiniLM checkpoint handles Arabic, French, and English — no preprocessing needed. It's also far smaller than BGE-M3 (~100MB vs ~2GB), which keeps the `worker-low` image and cold-start time down at the cost of some retrieval quality.

**Worker init pattern**:
```python
from celery.signals import worker_process_init

@worker_process_init.connect
def load_model(**kwargs):
    from core.embeddings import _load_model
    _load_model()
```
`_load_model()` sets a module-level `_model` variable. Subsequent calls to `embed_text()` use it without reloading.

**Model cache**: HuggingFace caches to `~/.cache/huggingface/hub/` by default. In Docker, the `worker-low` service mounts `bge_model_cache:/root/.cache/huggingface` (volume name predates this correction, left as-is to avoid an unnecessary infra rename) — weights persist across container restarts.

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

**Rationale**: Without a lock, two simultaneous creates (or a create + update race) could double-queue the same listing's embed task. The lock ensures only one task writes the vector at a time. 30s is conservative — MiniLM inference on a 300-token listing takes well under 2s on CPU.

---

## Roommate Match Query Strategy

**Decision**: Single SQL statement with 5 pgvector `<=>` cosine distance operators.

**Rationale**: FR-006 requires "5 separate pgvector cosine similarity queries (one per dim_* column)". A single SQL query with 5 `<=>` operators satisfies the spirit (one cosine op per dimension, computed in pgvector not Python) while avoiding 5 round-trips. This is more efficient and equally correct.

**Query shape**:
```sql
SELECT
    sp.user_id,
    ROUND((GREATEST(0, 1 - (dim_sleep      <=> :sv_sleep))
         + GREATEST(0, 1 - (dim_study      <=> :sv_study))
         + GREATEST(0, 1 - (dim_cleanliness<=> :sv_clean))
         + GREATEST(0, 1 - (dim_guests     <=> :sv_guests))
         + GREATEST(0, 1 - (dim_budget     <=> :sv_budget))) / 5.0, 4) AS score,
    GREATEST(0, 1 - (dim_sleep       <=> :sv_sleep))       AS sleep,
    GREATEST(0, 1 - (dim_study       <=> :sv_study))       AS study,
    GREATEST(0, 1 - (dim_cleanliness <=> :sv_clean))       AS cleanliness,
    GREATEST(0, 1 - (dim_guests      <=> :sv_guests))      AS guests,
    GREATEST(0, 1 - (dim_budget      <=> :sv_budget))      AS budget
FROM student_profiles sp
WHERE sp.user_id != :current_user_id
  AND sp.dim_sleep IS NOT NULL
ORDER BY score DESC
LIMIT 20;
```
Cosine similarity = 1 − cosine distance. pgvector `<=>` returns distance in `[0, 2]` (0=identical, 2=opposite), so raw similarity ranges `[-1, 1]`.

**Correction (2026-07-21)**: the first shipped version omitted `GREATEST(0, …)`, so orthogonal/negative-similarity pairs returned negative dimension scores — found during a full-system test pass. Spec SC-003 requires every dimension in `[0, 1]`; flooring at 0 (rather than rescaling the whole range with `(sim+1)/2`) was chosen because it keeps a "not compatible" dimension reading as ~0 instead of inflating it to a false-medium ~0.5, and it doesn't disturb `test_opposite_sleep_low_score`'s existing `< 0.4` assertion for orthogonal test vectors.

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
