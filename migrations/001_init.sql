-- SOC Plan Finder schema v1
-- Run this once against your Neon/Supabase database.

CREATE TABLE IF NOT EXISTS providers (
    id              SERIAL PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,
    allow_multiple  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plans (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    premium     NUMERIC(12, 2) NOT NULL CHECK (premium >= 0),
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plans_provider ON plans(provider_id);
CREATE INDEX IF NOT EXISTS idx_plans_enabled ON plans(enabled);

CREATE TABLE IF NOT EXISTS exclusion_rules (
    id         SERIAL PRIMARY KEY,
    plan_a_id  INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    plan_b_id  INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (plan_a_id <> plan_b_id)
);

-- Canonical ordering so (A, B) and (B, A) cannot both exist.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_exclusion_pair
    ON exclusion_rules (LEAST(plan_a_id, plan_b_id), GREATEST(plan_a_id, plan_b_id));
