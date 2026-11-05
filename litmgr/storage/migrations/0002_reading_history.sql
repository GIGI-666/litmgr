-- 阅读历史：记录最近阅读的论文，以及关闭阅读窗口时的页面状态。
-- 每篇论文最多一行（paper_id 为主键）；“只保留最近 N 篇”由仓库层负责裁剪。
-- state_json 是界面状态（PDF 页码/缩放、翻译滚动位置、窗口布局……）的 JSON，
-- 结构完全由界面层决定，数据库不关心内部格式，因此以后增加状态项无需再改表。
CREATE TABLE reading_history (
    paper_id    INTEGER PRIMARY KEY REFERENCES paper(id) ON DELETE CASCADE,
    last_opened TEXT    NOT NULL,
    state_json  TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_reading_history_time ON reading_history(last_opened DESC);
