-- Esquema para PostgreSQL (Neon en producción).
-- Equivalente al de SQLite, con tipos propios de Postgres.

CREATE TABLE IF NOT EXISTS sessions (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id          SERIAL PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

-- Tarjetas de estudio con datos de repaso espaciado (SM-2).
CREATE TABLE IF NOT EXISTS flashcards (
    id            SERIAL PRIMARY KEY,
    session_id    INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    question      TEXT NOT NULL,
    answer        TEXT NOT NULL,
    easiness      REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_due ON flashcards(due_date);
