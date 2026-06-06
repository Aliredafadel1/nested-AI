-- Migration 002: RLHF feedback + IP fraud tracking
-- Idempotent — safe to run multiple times

-- RLHF: store per-turn user ratings on agent responses
CREATE TABLE IF NOT EXISTS response_feedback (
    id          SERIAL PRIMARY KEY,
    session_id  VARCHAR(100) NOT NULL,
    turn_index  INTEGER NOT NULL DEFAULT 0,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating      SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    query_text  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_response_feedback_session ON response_feedback(session_id);
CREATE INDEX IF NOT EXISTS idx_response_feedback_user    ON response_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_response_feedback_good    ON response_feedback(rating) WHERE rating = 1;

-- Fraud: capture IP at listing creation time
ALTER TABLE listings ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);
CREATE INDEX IF NOT EXISTS idx_listings_ip ON listings(ip_address) WHERE ip_address IS NOT NULL;
