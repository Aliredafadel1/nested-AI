# Implementation Plan: Phase 1 — Foundation

**Branch**: `001-foundation` | **Date**: 2026-06-05 | **Spec**: specs/001-foundation/spec.md

## Summary

Build the full data layer, Docker infrastructure, JWT auth, and listings CRUD API. No AI features. Phase 2a depends on this being complete and all tests green.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 async, asyncpg, redis-py, minio, celery, passlib, python-jose  
**Storage**: PostgreSQL 16 + pgvector, Redis 7, MinIO  
**Testing**: pytest + pytest-asyncio against real containers  
**Target Platform**: Docker Compose (local dev + VPS prod)  
**Project Type**: Modular monolith web service + React frontend (frontend in Phase 3)

## Constitution Check

- ✅ Module boundaries: users and housing modules only — no cross-imports
- ✅ Security: JWT in response body (not cookie), refresh as HttpOnly cookie, bcrypt 12, magic bytes
- ✅ No LLM calls in Phase 1
- ✅ No WebSockets
- ✅ Soft delete enforced (FR-008)

## Project Structure

```
nestai/
├── Dockerfile
├── docker/
│   ├── docker-compose.yml
│   └── deploy.yml
├── .env.dev
├── .gitignore
├── requirements.txt
├── migrations/
│   └── init.sql          # 18 tables, HNSW indexes, pg_trgm, seed unis + neighbourhoods
├── seed/
│   └── listings.sql      # 50 Lebanese listings
├── core/
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # AsyncSession + sync for Celery
│   ├── redis.py          # 3 clients + RedisKeys (16 patterns)
│   ├── storage.py        # MinIO + 5 buckets + magic byte validation
│   ├── security.py       # JWT + bcrypt + rate limit middleware + injection sanitizer
│   ├── logging.py        # structlog + RequestIDMiddleware
│   ├── celery_config.py  # 4 queues + 8 Beat tasks
│   ├── embeddings.py     # BGE-M3 stub (implemented in Phase 2a)
│   └── llm_router.py     # LLM router stub (implemented in Phase 2b)
├── modules/
│   ├── users/            # register, login, refresh, logout, onboarding
│   ├── housing/          # listings CRUD + save + file upload
│   └── [8 stub modules]  # roommate, agent, fraud, contracts, area_intel, estimator, notifications, reputation
├── app/
│   └── main.py           # FastAPI factory + lifespan + all routers
├── tests/
│   └── test_api_listings.py
└── specs/
    └── all_modules.yaml
```

## API Contracts

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /auth/register | None | Register student or landlord |
| POST | /auth/login | None | Login, get access token + refresh cookie |
| POST | /auth/refresh | Cookie | Rotate refresh token |
| POST | /auth/logout | Bearer | Delete refresh token from Redis |
| GET | /listings | Optional | Browse listings (with filters) |
| POST | /listings | Landlord | Create listing |
| GET | /listings/{id} | Optional | Get single listing |
| PUT | /listings/{id} | Landlord (own) | Update listing |
| DELETE | /listings/{id} | Landlord (own) | Soft delete (status → inactive) |
| POST | /listings/{id}/save | Student | Save listing |
| GET | /listings/saved | Student | Get saved listings |
| POST | /users/onboarding | Student | Store 8-question preferences |
| POST | /listings/{id}/photos | Landlord (own) | Upload photos (magic byte validated) |
| GET | /health | None | Health check |

## Redis Keys Used

- `refresh:{user_id}` — String, 7d TTL, hashed refresh token
- `rate:ip:{ip}:{endpoint}` — String, 60s TTL, sliding window counter

## Celery

Workers start in Phase 1 but no tasks are dispatched yet. Beat schedule configured for Phase 2.

## Test Plan

`tests/test_api_listings.py` covers:
- Auth flow (register → login → protected endpoint → refresh → logout)
- Listings CRUD (create, read, update, soft-delete, ownership enforcement)
- Photo upload (valid file, invalid magic bytes, size limit)
- Save/unsave listing
- Filter by neighbourhood and price
