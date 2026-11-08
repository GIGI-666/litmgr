-- 字段分组独立保存，允许先建空分组；由 FieldRepo / FieldService 维护。
-- 旧库按字段原有顺序继承所有分组（包含已归档字段），不修改论文内容。
CREATE TABLE IF NOT EXISTS field_group (
    name       TEXT PRIMARY KEY NOT NULL CHECK (length(trim(name)) > 0),
    sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO field_group(name, sort_order)
SELECT group_name, MIN(sort_order)
FROM field_def
WHERE group_name <> ''
GROUP BY group_name;
