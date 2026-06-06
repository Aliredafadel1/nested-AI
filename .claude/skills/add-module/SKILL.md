---
name: add-module
description: Scaffold a new NestAI domain module following the modular monolith pattern exactly.
disable-model-invocation: true
---
Create a new module named: $ARGUMENTS

Steps:

1. Read `modules/users/` as the reference implementation pattern.
2. Read `specs/all_modules.yaml` to understand the spec format for the new entry.

3. Create `modules/<name>/` with these files:
   - `__init__.py` — empty
   - `models.py` — SQLAlchemy ORM models, all table names snake_case
   - `schemas.py` — Pydantic schemas for all request/response types; use `model_config = ConfigDict(from_attributes=True)`
   - `repository.py` — repository class with `__init__(self, db: AsyncSession)`. This file is private — never imported outside this module.
   - `service.py` — service class with `__init__(self, db: AsyncSession, redis: Redis)`. This is the only cross-module interface.
   - `router.py` — FastAPI APIRouter with `prefix="/<name>"` and `tags=["<name>"]`. No business logic here.

4. Register the router in `app/main.py` following the existing pattern.

5. Add table definitions to `migrations/init.sql`.

6. Add the module spec entry to `specs/all_modules.yaml` with at minimum: `module`, `endpoints`, and `tables` keys.

7. CRITICAL: Do not import `modules/<name>/repository.py` from any other module. If another module needs data from this one, add a method to `modules/<name>/service.py`.

8. Verify scaffold: `docker compose exec api python -c "from modules.<name> import router; print('OK')"`.
