# Data Model: Phase 2a — Embeddings + Roommate Matching

## Schema Changes (Migration 002a)

### student_profiles — 5 new columns

```sql
ALTER TABLE student_profiles
    ADD COLUMN IF NOT EXISTS dim_sleep       vector(1024),
    ADD COLUMN IF NOT EXISTS dim_study       vector(1024),
    ADD COLUMN IF NOT EXISTS dim_cleanliness vector(1024),
    ADD COLUMN IF NOT EXISTS dim_guests      vector(1024),
    ADD COLUMN IF NOT EXISTS dim_budget      vector(1024);
```

**Invariants**:
- After `embed_profile` task runs successfully: all 5 `dim_*` columns + `embedding` column are non-NULL.
- Before `embed_profile` runs (or if it fails all 3 retries): columns may be NULL. `GET /roommate/matches` returns 422 if caller's own `dim_sleep IS NULL`.
- Null preference fields use fallback text `"unspecified"` — `dim_*` columns are always populated after onboarding, never left NULL after a successful task run.

### New HNSW Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_sp_dim_sleep
    ON student_profiles USING hnsw (dim_sleep vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_sp_dim_study
    ON student_profiles USING hnsw (dim_study vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_sp_dim_cleanliness
    ON student_profiles USING hnsw (dim_cleanliness vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_sp_dim_guests
    ON student_profiles USING hnsw (dim_guests vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_sp_dim_budget
    ON student_profiles USING hnsw (dim_budget vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

## No New Tables

`roommate_requests` already exists from Phase 1 migration. No additional tables needed in Phase 2a.

---

## Updated listings.embedding Lifecycle

| Event | Trigger | Task |
|---|---|---|
| `POST /listings` | housing service | `embed_listing.delay(listing_id)` |
| `PUT /listings/{id}` | housing service | `embed_listing.delay(listing_id)` |
| Soft delete | No re-embed | — |
| Nightly batch | Celery beat | `batch_embed_seed_data` — re-embeds all NULL embeddings |

**Lock**: `lock:embed:{listing_id}` (Redis SET NX, 30s TTL) prevents duplicate concurrent tasks.

**Cache**: `embed:{sha256[:16]}` (Redis, 48h TTL) — identical text (e.g. unchanged listing re-submitted) returns cached vector without BGE-M3 inference.

---

## Redis Key Additions

Two new keys added to `RedisKeys` in `core/redis.py`:

| Key Pattern | TTL | Purpose |
|---|---|---|
| `embed:{text_hash}` | 48h | Cache BGE-M3 output for a given input text |
| `lock:embed:{listing_id}` | 30s | Distributed lock preventing duplicate embed tasks |

---

## Roommate Match Response Shape

```python
class DimensionScores(BaseModel):
    sleep:       float  # [0, 1]
    study:       float
    cleanliness: float
    guests:      float
    budget:      float

class MatchOut(BaseModel):
    user_id:    int
    score:      float        # average of 5 dimensions, [0, 1]
    dimensions: DimensionScores
```
