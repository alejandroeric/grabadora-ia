-- Esquema de la base de datos (SQLite).
-- Dos tablas relacionadas por foreign key: sessions 1---N messages.

CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    transcript  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

-- Tarjetas de estudio con datos de repaso espaciado (SM-2).
CREATE TABLE IF NOT EXISTS flashcards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER,
    question     TEXT NOT NULL,
    answer       TEXT NOT NULL,
    easiness     REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions  INTEGER NOT NULL DEFAULT 0,
    due_date     TEXT NOT NULL DEFAULT (date('now')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_flashcards_due ON flashcards(due_date);
