-- Phase 2a Migration: add 5 dimension sub-embedding columns to student_profiles
-- Idempotent: safe to run multiple times

ALTER TABLE student_profiles
    ADD COLUMN IF NOT EXISTS dim_sleep        vector(384),
    ADD COLUMN IF NOT EXISTS dim_study        vector(384),
    ADD COLUMN IF NOT EXISTS dim_cleanliness  vector(384),
    ADD COLUMN IF NOT EXISTS dim_guests       vector(384),
    ADD COLUMN IF NOT EXISTS dim_budget       vector(384);

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
