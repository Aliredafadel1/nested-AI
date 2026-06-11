-- NestAI Database Schema
-- Idempotent: safe to run multiple times
-- Table order: leaf tables first (no FK deps), then tables that reference them

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─── UNIVERSITIES (no deps) ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS universities (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(200) UNIQUE NOT NULL,
    lat     NUMERIC(10,7) NOT NULL,
    lng     NUMERIC(10,7) NOT NULL
);

-- ─── AREA INTELLIGENCE (no deps) ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS neighborhoods (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) UNIQUE NOT NULL,
    name_ar         VARCHAR(100),
    city            VARCHAR(100) DEFAULT 'Beirut',
    electricity     NUMERIC(3,1),   -- hours per day
    generator_cost  INTEGER,         -- USD/month
    internet        SMALLINT CHECK (internet BETWEEN 1 AND 5),
    transport       SMALLINT CHECK (transport BETWEEN 1 AND 5),
    safety          SMALLINT CHECK (safety BETWEEN 1 AND 5),
    student_vibe    SMALLINT CHECK (student_vibe BETWEEN 1 AND 5),
    lat             NUMERIC(10,7),
    lng             NUMERIC(10,7)
);

-- ─── USERS (no deps) ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('student', 'landlord', 'admin')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_profiles (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    university_id       INTEGER REFERENCES universities(id),
    budget_min          INTEGER,
    budget_max          INTEGER,
    sleep_schedule      VARCHAR(20) CHECK (sleep_schedule IN ('early_bird', 'night_owl', 'flexible')),
    study_habits        VARCHAR(20) CHECK (study_habits IN ('quiet', 'moderate', 'flexible')),
    cleanliness         VARCHAR(20) CHECK (cleanliness IN ('high', 'medium', 'low')),
    guests              VARCHAR(20) CHECK (guests IN ('never', 'rarely', 'sometimes', 'often')),
    language            VARCHAR(20) CHECK (language IN ('arabic', 'french', 'english', 'mixed')),
    priorities          JSONB DEFAULT '[]',
    embedding           vector(1024),
    preference_vector   vector(1024),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS landlord_profiles (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone           VARCHAR(30),
    phone_verified  BOOLEAN DEFAULT FALSE,
    reputation_score NUMERIC(3,2) DEFAULT 0.00
);

-- ─── HOUSING ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS listings (
    id                  SERIAL PRIMARY KEY,
    landlord_id         INTEGER NOT NULL REFERENCES users(id),
    neighbourhood_id    INTEGER NOT NULL REFERENCES neighborhoods(id),
    title               VARCHAR(300) NOT NULL,
    description         TEXT,
    price               INTEGER NOT NULL,  -- USD/month
    bedrooms            SMALLINT NOT NULL,
    bathrooms           SMALLINT DEFAULT 1,
    area_sqm            INTEGER,
    amenities           JSONB DEFAULT '{}',
    address             VARCHAR(300),
    lat                 NUMERIC(10,7),
    lng                 NUMERIC(10,7),
    status              VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    fraud_score         NUMERIC(4,3) DEFAULT 0.000,
    embedding           vector(1024),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS listing_photos (
    id          SERIAL PRIMARY KEY,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    minio_key   VARCHAR(500) NOT NULL,
    phash       VARCHAR(64),
    is_primary  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS listing_verifications (
    id              SERIAL PRIMARY KEY,
    listing_id      INTEGER UNIQUE NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    phone_verified  BOOLEAN DEFAULT FALSE,
    photos_reviewed BOOLEAN DEFAULT FALSE,
    price_in_range  BOOLEAN DEFAULT FALSE,
    verified_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS saved_listings (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    saved_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, listing_id)
);

-- ─── FRAUD ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fraud_reports (
    id              SERIAL PRIMARY KEY,
    listing_id      INTEGER NOT NULL REFERENCES listings(id),
    score           NUMERIC(4,3) DEFAULT 0.000,
    price_zscore    NUMERIC(6,3),
    evidence        JSONB DEFAULT '{"price_flags": [], "phone_flags": [], "photo_flags": [], "text_flags": []}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── ROOMMATE ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS roommate_requests (
    id              SERIAL PRIMARY KEY,
    from_user_id    INTEGER NOT NULL REFERENCES users(id),
    to_user_id      INTEGER NOT NULL REFERENCES users(id),
    score           NUMERIC(4,3),
    dimensions      JSONB DEFAULT '{}',
    status          VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roommate_messages (
    id          SERIAL PRIMARY KEY,
    request_id  INTEGER NOT NULL REFERENCES roommate_requests(id) ON DELETE CASCADE,
    sender_id   INTEGER NOT NULL REFERENCES users(id),
    content     TEXT NOT NULL CHECK (char_length(content) <= 1000),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── CONTRACTS ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contracts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    minio_key   VARCHAR(500) NOT NULL,
    ocr_used    BOOLEAN DEFAULT FALSE,
    analysis    JSONB,
    status      VARCHAR(30) DEFAULT 'pending' CHECK (status IN ('pending', 'ocr_running', 'analyzing', 'complete', 'failed')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── ESTIMATOR ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_estimates (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    listing_id      INTEGER REFERENCES listings(id),
    university_id   INTEGER REFERENCES universities(id),
    rent            INTEGER,
    generator       INTEGER,
    water           INTEGER DEFAULT 15,
    internet        INTEGER DEFAULT 30,
    transport       INTEGER,
    total_monthly   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── NOTIFICATIONS ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notifications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50) NOT NULL,
    payload     JSONB DEFAULT '{}',
    read        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── REPUTATION ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS landlord_reviews (
    id              SERIAL PRIMARY KEY,
    landlord_id     INTEGER NOT NULL REFERENCES users(id),
    reviewer_id     INTEGER NOT NULL REFERENCES users(id),
    listing_id      INTEGER REFERENCES listings(id),
    maintenance     SMALLINT CHECK (maintenance BETWEEN 1 AND 5),
    responsiveness  SMALLINT CHECK (responsiveness BETWEEN 1 AND 5),
    honesty         SMALLINT CHECK (honesty BETWEEN 1 AND 5),
    hidden_fees     SMALLINT CHECK (hidden_fees BETWEEN 1 AND 5),
    ai_summary      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (landlord_id, reviewer_id, listing_id)
);

-- ─── AGENT ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS agent_sessions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id  VARCHAR(100) UNIQUE NOT NULL,
    state       JSONB DEFAULT '{}',
    history     JSONB DEFAULT '[]',
    summary     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_memory (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_areas     JSONB DEFAULT '[]',
    preference_vector   vector(1024),
    liked_count         INTEGER DEFAULT 0,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id          SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('listing', 'area', 'contract_clause', 'housing_faq')),
    source_id   INTEGER,
    chunk_text  TEXT NOT NULL,
    embedding   vector(1024),
    language    VARCHAR(10) DEFAULT 'en',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── INDEXES ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_listings_neighbourhood ON listings(neighbourhood_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
CREATE INDEX IF NOT EXISTS idx_listings_landlord ON listings(landlord_id);
CREATE INDEX IF NOT EXISTS idx_listing_photos_listing ON listing_photos(listing_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_fraud_listing ON fraud_reports(listing_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user ON agent_sessions(user_id);

-- HNSW vector indexes (used by Phase 2a+)
CREATE INDEX IF NOT EXISTS idx_listings_embedding ON listings
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_student_profiles_embedding ON student_profiles
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding ON rag_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- pg_trgm for hybrid text search
CREATE INDEX IF NOT EXISTS idx_listings_title_trgm ON listings USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_listings_description_trgm ON listings USING gin (description gin_trgm_ops);

-- ─── SEED: UNIVERSITIES ──────────────────────────────────────────────────────

INSERT INTO universities (name, lat, lng) VALUES
    ('American University of Beirut (AUB)', 33.9003, 35.4784),
    ('Lebanese American University - Beirut (LAU)', 33.8938, 35.4897),
    ('Saint Joseph University (USJ)', 33.8889, 35.5025),
    ('Lebanese University - Hadath (LU)', 33.8242, 35.5353),
    ('Haigazian University', 33.8896, 35.4972),
    ('Notre Dame University - Louaize (NDU)', 33.9958, 35.6228),
    ('Lebanese International University - Beirut (LIU)', 33.8651, 35.5106),
    ('Lebanese American University - Byblos (LAU Byblos)', 34.2533, 35.6486),
    ('University of Balamand', 34.3728, 35.7283),
    ('Modern University for Business and Science (MUBS)', 33.8830, 35.5007)
ON CONFLICT (name) DO NOTHING;

-- ─── SEED: NEIGHBOURHOODS ────────────────────────────────────────────────────

INSERT INTO neighborhoods (name, name_ar, electricity, generator_cost, internet, transport, safety, student_vibe, lat, lng) VALUES
    -- electricity = avg EDL hours/day (post-2019 crisis reality)
    -- generator_cost = typical private generator subscription USD/month
    ('Hamra',       'الحمرا',       12, 40, 4, 5, 4, 5, 33.8989, 35.4788),
    ('Gemmayzeh',   'الجميزة',      12, 42, 4, 4, 4, 5, 33.8916, 35.5144),
    ('Achrafieh',   'الأشرفية',     18, 28, 5, 4, 5, 4, 33.8888, 35.5133),  -- one of Beirut''s best EDL zones
    ('Mar Mikhael', 'مار مخايل',    12, 42, 4, 4, 3, 5, 33.8854, 35.5203),
    ('Verdun',      'فردان',        20, 22, 5, 3, 5, 3, 33.8820, 35.4893),   -- best EDL zone, residential
    ('Badaro',      'بدارو',        14, 38, 4, 3, 4, 4, 33.8777, 35.5072),
    ('Ras Beirut',  'رأس بيروت',    12, 40, 4, 4, 4, 5, 33.8969, 35.4742),
    ('Dekwaneh',    'الدكوانة',      8, 50, 3, 3, 3, 3, 33.8898, 35.5570)   -- outer suburb, worst EDL hours
ON CONFLICT (name) DO UPDATE SET
    electricity    = EXCLUDED.electricity,
    generator_cost = EXCLUDED.generator_cost;
