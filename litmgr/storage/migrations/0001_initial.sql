-- 初始数据库结构（详见 planning/02_数据库设计.md）

CREATE TABLE paper (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    read_status TEXT NOT NULL DEFAULT 'unread',
    rating      INTEGER NOT NULL DEFAULT 0,
    archived    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE field_def (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    type         TEXT NOT NULL DEFAULT 'longtext',
    options_json TEXT NOT NULL DEFAULT '[]',
    aliases_json TEXT NOT NULL DEFAULT '[]',
    role         TEXT,
    group_name   TEXT NOT NULL DEFAULT '',
    sort_order   INTEGER NOT NULL DEFAULT 0,
    show_in_list INTEGER NOT NULL DEFAULT 0,
    archived     INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX ux_field_role ON field_def(role) WHERE role IS NOT NULL;

CREATE TABLE field_value (
    paper_id   INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    field_id   INTEGER NOT NULL REFERENCES field_def(id) ON DELETE CASCADE,
    value_text TEXT NOT NULL DEFAULT '',
    value_json TEXT,
    PRIMARY KEY (paper_id, field_id)
);
CREATE INDEX ix_field_value_field ON field_value(field_id);

CREATE TABLE paper_file (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id     INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL,
    subtype      TEXT NOT NULL DEFAULT '',
    rel_path     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    sha256       TEXT NOT NULL DEFAULT '',
    added_at     TEXT NOT NULL
);
CREATE INDEX ix_paper_file_paper ON paper_file(paper_id);

CREATE TABLE tag (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT ''
);
CREATE TABLE paper_tag (
    paper_id INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, tag_id)
);

CREATE TABLE collection (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE paper_collection (
    paper_id      INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    collection_id INTEGER NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, collection_id)
);

CREATE TABLE saved_view (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    query_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE note (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX ix_note_paper ON note(paper_id);

CREATE TABLE change_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    field_id   INTEGER,
    field_name TEXT NOT NULL DEFAULT '',
    old_value  TEXT NOT NULL DEFAULT '',
    new_value  TEXT NOT NULL DEFAULT '',
    changed_at TEXT NOT NULL,
    undone     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_change_log_paper ON change_log(paper_id);

CREATE TABLE pending_content (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES paper(id) ON DELETE CASCADE,
    label    TEXT NOT NULL DEFAULT '',
    content  TEXT NOT NULL
);

-- 全文索引：trigram 分词，支持中文子串检索（>=3 字符）；更短的查询用 LIKE 回退
-- source: 'field' 表示来自字段值；'file:<id>' 表示来自某个翻译文件正文
CREATE VIRTUAL TABLE search_index USING fts5(
    paper_id UNINDEXED,
    field_id UNINDEXED,
    source   UNINDEXED,
    content,
    tokenize = 'trigram'
);
