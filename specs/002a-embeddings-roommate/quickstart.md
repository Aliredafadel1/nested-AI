# Quickstart Validation: Phase 2a — Embeddings + Roommate Matching

## Prerequisites

- Phase 1 complete and all tests passing
- `docker compose up -d` with all services healthy
- Phase 2a migration applied: `docker compose exec db psql -U nestai -d nestai -f /migrations/002a_add_profile_dim_vectors.sql`
- `worker-low` service running (MiniLM downloads on first start — allow 2-3 min on first run)

---

## Scenario 1 — Listing embedding on create

```bash
# 1. Create a listing
curl -s -X POST http://localhost:8000/listings \
  -H "Authorization: Bearer <landlord_token>" \
  -H "Content-Type: application/json" \
  -d '{"neighbourhood_id":1,"title":"Test embed listing","price":500,"bedrooms":1}' \
  | jq .id

# 2. Wait ~5s for worker-low, then verify embedding populated
docker compose exec db psql -U nestai -d nestai \
  -c "SELECT id, title, embedding IS NOT NULL as has_embedding FROM listings ORDER BY id DESC LIMIT 1;"

# Expected: has_embedding = t
```

---

## Scenario 2 — Listing re-embedding on update

```bash
# Update the listing — embedding must refresh
curl -s -X PUT http://localhost:8000/listings/<id> \
  -H "Authorization: Bearer <landlord_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated title"}'

# Wait ~5s, verify updated_at on listing and embedding is still non-null
docker compose exec db psql -U nestai -d nestai \
  -c "SELECT id, title, embedding IS NOT NULL FROM listings WHERE id = <id>;"
```

---

## Scenario 3 — Profile embedding after onboarding

```bash
# Submit onboarding
curl -s -X POST http://localhost:8000/users/onboarding \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "university_id": 1,
    "budget_min": 400, "budget_max": 700,
    "sleep_schedule": "night_owl",
    "study_habits": "quiet",
    "cleanliness": "high",
    "guests": "rarely",
    "language": "mixed"
  }'

# Wait ~10s, verify all 6 vectors populated
docker compose exec db psql -U nestai -d nestai -c "
  SELECT
    embedding IS NOT NULL       AS full_embed,
    dim_sleep IS NOT NULL       AS dim_sleep,
    dim_study IS NOT NULL       AS dim_study,
    dim_cleanliness IS NOT NULL AS dim_clean,
    dim_guests IS NOT NULL      AS dim_guests,
    dim_budget IS NOT NULL      AS dim_budget
  FROM student_profiles WHERE user_id = <student_id>;"

# Expected: all columns = t
```

---

## Scenario 4 — Roommate match returns 5 dimensions

```bash
curl -s http://localhost:8000/roommate/matches \
  -H "Authorization: Bearer <student_token>" | jq '.[0]'

# Expected shape:
# {
#   "user_id": ...,
#   "score": 0.82,
#   "dimensions": {
#     "sleep": 0.95,
#     "study": 0.71,
#     "cleanliness": 0.68,
#     "guests": 0.90,
#     "budget": 0.86
#   }
# }
```

---

## Scenario 5 — Opposite sleep schedules produce low sleep score

```bash
# Jawad = night_owl, Omar = early_bird (both seeded)
# After their profiles are embedded:
curl -s http://localhost:8000/roommate/matches \
  -H "Authorization: Bearer <jawad_token>" | jq '.[] | select(.user_id == <omar_id>) | .dimensions.sleep'

# Expected: < 0.4
```

---

## Scenario 6 — 422 if no embedding yet

```bash
# Register a brand-new student who hasn't completed onboarding
curl -s -X POST http://localhost:8000/auth/register \
  -d '{"email":"notembed@test.com","password":"Test1234!","role":"student"}' \
  -H "Content-Type: application/json"

curl -s http://localhost:8000/roommate/matches \
  -H "Authorization: Bearer <new_student_token>"

# Expected: HTTP 422 with message about completing onboarding
```

---

## Run Full Test Suite

```bash
docker compose exec api pytest tests/test_embeddings.py -v
```

**Expected**: All tests pass — dimension check (384), normalisation, batch efficiency, all 6 profile vector fields, opposite sleep score < 0.4.

---

## Verify MiniLM Loaded Once

```bash
docker compose logs worker-low | grep "MiniLM"
# Expected: exactly ONE line: "MiniLM model loaded"
# No repeated loads across multiple embed tasks
```

---

## Batch Seed Embeddings

```bash
# Embed all 50 seed listings (run once after applying migration)
docker compose exec api python -c "
from modules.housing.tasks import batch_embed_seed_data
batch_embed_seed_data.delay()
"

# Verify after ~2 minutes
docker compose exec db psql -U nestai -d nestai \
  -c "SELECT COUNT(*) FROM listings WHERE embedding IS NOT NULL;"
# Expected: 50
```
