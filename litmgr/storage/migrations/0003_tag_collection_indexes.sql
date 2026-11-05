-- 性能优化：按标签 / 分组反查论文、统计各标签/分组的论文数时走索引（原主键只覆盖“按论文查”）。
-- 只加索引，不改任何数据与表结构，功能完全不变。
CREATE INDEX IF NOT EXISTS ix_paper_tag_tag ON paper_tag(tag_id, paper_id);
CREATE INDEX IF NOT EXISTS ix_paper_collection_coll ON paper_collection(collection_id, paper_id);
