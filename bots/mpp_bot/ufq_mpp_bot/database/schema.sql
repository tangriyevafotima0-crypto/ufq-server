PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    username TEXT,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS directions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction_id INTEGER NOT NULL REFERENCES directions(id) ON DELETE CASCADE,
    mentor_id INTEGER NOT NULL REFERENCES users(telegram_id),
    invite_code TEXT UNIQUE,
    invite_code_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cell_members (
    cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
    partner_id INTEGER NOT NULL REFERENCES users(telegram_id),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    PRIMARY KEY (cell_id, partner_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id INTEGER NOT NULL REFERENCES cells(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(telegram_id),
    title TEXT NOT NULL,
    description TEXT,
    deadline TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(telegram_id),
    status TEXT CHECK(status IN ('kutilmoqda', 'jarayonda', 'bajardi', 'bajarmadi')) DEFAULT 'kutilmoqda',
    submitted_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS mock_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(telegram_id),
    direction_id INTEGER NOT NULL REFERENCES directions(id),
    entered_by INTEGER NOT NULL REFERENCES users(telegram_id),
    score REAL NOT NULL,
    date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(telegram_id),
    reminder_type TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_submissions_task_user ON submissions(task_id, user_id);
CREATE INDEX IF NOT EXISTS idx_cells_mentor ON cells(mentor_id);
CREATE INDEX IF NOT EXISTS idx_cell_members_partner ON cell_members(partner_id);
CREATE INDEX IF NOT EXISTS idx_mock_results_user ON mock_results(user_id);

-- Defense-in-depth: enforce the 3-partner-per-cell cap at the DB layer too,
-- so a race between two concurrent INSERTs (app-level check passing for both)
-- cannot push a cell to 4+ active partners.
CREATE TRIGGER IF NOT EXISTS trg_cell_capacity_insert
BEFORE INSERT ON cell_members
WHEN NEW.is_active = 1
BEGIN
    SELECT RAISE(ABORT, 'CELL_FULL')
    WHERE (
        SELECT COUNT(*) FROM cell_members
        WHERE cell_id = NEW.cell_id AND is_active = 1
    ) >= 3;
END;

CREATE TRIGGER IF NOT EXISTS trg_cell_capacity_update
BEFORE UPDATE OF is_active, cell_id ON cell_members
WHEN NEW.is_active = 1 AND (OLD.is_active = 0 OR NEW.cell_id != OLD.cell_id)
BEGIN
    SELECT RAISE(ABORT, 'CELL_FULL')
    WHERE (
        SELECT COUNT(*) FROM cell_members
        WHERE cell_id = NEW.cell_id AND is_active = 1 AND partner_id != NEW.partner_id
    ) >= 3;
END;
