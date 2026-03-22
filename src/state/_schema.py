"""SQLite schema DDL for the state management layer.

Contains table definitions, indexes, and schema version tracking.
6 main tables + schema_version + 8 indexes.
"""

SCHEMA_SQL = """
-- Table 1: projects
CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    path            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'pending',
    languages       TEXT NOT NULL DEFAULT '[]',
    file_count      INTEGER NOT NULL DEFAULT 0,
    function_count  INTEGER NOT NULL DEFAULT 0,
    class_count     INTEGER NOT NULL DEFAULT 0,
    total_lines     INTEGER NOT NULL DEFAULT 0
);

-- Table 2: modules
CREATE TABLE IF NOT EXISTS modules (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    name            TEXT NOT NULL,
    files           TEXT NOT NULL DEFAULT '[]',
    file_count      INTEGER NOT NULL DEFAULT 0,
    line_count      INTEGER NOT NULL DEFAULT 0,
    function_count  INTEGER NOT NULL DEFAULT 0,
    class_count     INTEGER NOT NULL DEFAULT 0,
    is_utility      BOOLEAN NOT NULL DEFAULT 0,
    description     TEXT,
    UNIQUE(project_id, name),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Table 3: analysis_tasks
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    module_name     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    assigned_agent  TEXT,
    batch_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at    TEXT,
    UNIQUE(project_id, module_name),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Table 4: analysis_results
CREATE TABLE IF NOT EXISTS analysis_results (
    id                  TEXT PRIMARY KEY,
    task_id             TEXT NOT NULL,
    project_id          TEXT NOT NULL,
    module_name         TEXT NOT NULL,
    description         TEXT NOT NULL,
    public_interfaces   TEXT NOT NULL DEFAULT '[]',
    key_data_structures TEXT NOT NULL DEFAULT '[]',
    dependencies        TEXT NOT NULL DEFAULT '[]',
    dependents          TEXT NOT NULL DEFAULT '[]',
    patterns_identified TEXT NOT NULL DEFAULT '[]',
    detailed_analysis   TEXT,
    mermaid_diagram     TEXT,
    token_count         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, module_name),
    FOREIGN KEY (task_id) REFERENCES analysis_tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Table 5: checkpoints
CREATE TABLE IF NOT EXISTS checkpoints (
    id                      TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'in_progress',
    phase                   TEXT NOT NULL DEFAULT 'indexing',
    analyzed_modules        TEXT NOT NULL DEFAULT '[]',
    pending_modules         TEXT NOT NULL DEFAULT '[]',
    total_modules           INTEGER NOT NULL DEFAULT 0,
    total_tokens_processed  INTEGER NOT NULL DEFAULT 0,
    errors                  TEXT NOT NULL DEFAULT '[]',
    metadata                TEXT NOT NULL DEFAULT '{}',
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Table 6: doc_nodes
CREATE TABLE IF NOT EXISTS doc_nodes (
    id              TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL,
    path            TEXT NOT NULL,
    level           INTEGER NOT NULL,
    target          TEXT NOT NULL,
    token_budget    INTEGER NOT NULL,
    parent_path     TEXT,
    children_paths  TEXT NOT NULL DEFAULT '[]',
    content         TEXT,
    actual_tokens   INTEGER,
    status          TEXT NOT NULL DEFAULT 'planned',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, path),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_modules_project ON modules(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON analysis_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON analysis_tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_results_project ON analysis_results(project_id);
CREATE INDEX IF NOT EXISTS idx_results_module ON analysis_results(module_name);
CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON checkpoints(project_id);
CREATE INDEX IF NOT EXISTS idx_doc_nodes_project ON doc_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_doc_nodes_level ON doc_nodes(project_id, level);
"""
