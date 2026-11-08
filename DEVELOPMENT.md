# 开发接手指南

## 一、先建立可工作的基线

按 [README](README.md) 安装 Python 3.12 与 `requirements.txt`，运行环境自检，然后在四篇论文的库副本中确认主窗口、详情和 PDF/翻译双栏能打开。

项目目前以 Windows 验证为主；其他系统可按相同 Python 包结构运行，但需要自行验证 QtPdf/QtWebEngine 的系统依赖。

离屏测试（Windows PowerShell）：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:QT_QPA_FONTDIR='C:/Windows/Fonts'
$env:QTWEBENGINE_CHROMIUM_FLAGS='--no-sandbox --disable-gpu'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pyflakes litmgr tests
```

准备分享时的应用及分享工具测试基线为 **56 项通过**，导入测试使用固定临时小样，不依赖原维护者的私人目录。Qt 离屏平台不指定字体目录可能无法加载字体，导致测试 PDF 没有可搜索文字；不要把这个环境问题误当搜索功能回归。

上述环境变量只用于当前测试终端。测试后新开一个 PowerShell 运行真实 GUI，或移除这些设置：

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
Remove-Item Env:QT_QPA_FONTDIR -ErrorAction SilentlyContinue
Remove-Item Env:QTWEBENGINE_CHROMIUM_FLAGS -ErrorAction SilentlyContinue
```

## 二、目录和依赖方向

```text
litmgr/
  core/       领域模型、字段类型、查询、事件、配置
  storage/    SQLite、迁移、仓库、文献库文件系统
  services/   业务服务；app_context.py 是统一装配点
  importers/  卡片解析、文件分类和配对
  ui/         PySide6 主窗口、详情、阅读、对比和管理界面
planning/     数据库、模块、注释、维护文档
tests/        核心、导入、回归、阅读历史和界面测试
scripts/      环境检查、性能剖析、分享快照和技能打包
skill/        技能源码、ZIP、使用说明
shared_library/  交接的完整文献库快照
```

严格遵循 `ui → services → storage → core`；`importers` 只依赖 `core`。界面不写 SQL，不让底层反向引用窗口。

`AppContext` 组装所有仓库与服务。改数据由服务层发布 `Events.*`，窗口通过 `EventSubscriberMixin` 订阅并在关闭时退订。

## 三、数据与界面约定

- `Database.transaction()` 支持嵌套；多步数据修改要在事务中一起成功或回滚。`execute()` 在最外层事务之外才自动提交。
- 新表结构新建 `storage/migrations/NNNN_*.sql`，不要改已使用的旧迁移。`PRAGMA user_version` 管版本，升级前自动快照，恢复旧备份会补跑迁移。
- 标题/arXiv 等系统语义用字段的 `role` 识别，不能按可编辑的中文字段名判断。
- 新字段类型在 `core/field_types.py` 注册；编辑器在 `ui/field_widgets.py` 注册。过滤比较逻辑放 `FieldType.matches`。
- 字段分组存 `field_group`，归属在 `field_def.group_name`；空字符串为未分组。组改名/删除同时处理已归档字段，不能删除字段值。
- FTS5 trigram 索引规则见 [数据库设计](planning/02_数据库设计.md)；不足 3 字符用 LIKE 回退。
- `SearchService.run()` 返回的 `Paper` 仅带列表所需字段，需要完整内容时调用 `papers.get()`。
- 窗口位置/分栏存 `AppConfig.ui_state`；阅读器页面状态保存在阅读历史。不要另引入 QSettings。
- 新窗口方法使用 `guarded` 统一提示异常，按钮优先用 `make_button` / `add_buttons`。显示用户文本时注意 QLabel 自动识别 HTML。

详细模块入口和扩展位置见 [模块清单](planning/03_模块清单.md)。

## 四、业务数据快照如何使用和更新

`shared_library/` 的数据库、PDF、翻译、原始卡片及历史备份组成一个整体。不要只分享数据库或只分享 PDF 后期待还原同一状态。

- **推荐日常开发**：复制 `shared_library/` 到仓库外的新目录，用 `--library` 指向副本。
- **更新分享快照**：先退出正在编辑数据的操作，确保字段和笔记已保存；应用可保持运行，脚本通过 SQLite 在线备份读取已提交数据。

```powershell
.\.venv\Scripts\python.exe scripts\snapshot_library.py D:\my-library ..\litmgr-snapshot-new
```

可选附加 `--config` 指向自己的 `config.json`，导出设置副本；脚本清除其中本机库路径，保留偏好和窗口状态。命令拒绝覆盖已有目标。

检查新目录 `snapshot_manifest.json` 的论文数、字段数、文件数及哈希，启动其副本确认后，再由维护者在独立分支替换仓库中的 `shared_library/` 并提交。数据库二进制无法像代码一样逐行合并；多人不要并行提交各自的日常数据库。

快照脚本会验证数据库完整性、外键、登记文件和 SHA-256，排除锁、WAL/SHM/journal 和日志。若原文件在拍快照过程中变化，重新生成新快照；不要为了绕过检查去改清单哈希。

`.gitattributes` 对分享快照关闭文本换行转换，保证其他平台检出后，原 PDF、卡片和翻译仍与清单哈希一致；不要为统一代码风格批量重写快照里的文本文件。

## 五、修改并重新打包技能

共享的可编辑版本在 `skill/paper-translate-package/`：

- `SKILL.md`：输入、默认任务、全文翻译和交付流程。
- `references/translation-rules.md`：用户翻译要求。
- `references/litmgr-format.md`：导入兼容约定。
- `assets/card-template.txt`：初始模板快照；实际使用优先读当次模板。
- `scripts/paper_bundle.py`：标准库工具，负责快照、分段登记、卡片和最终文件包，不调用模型 API。
- `agents/openai.yaml`：显示名称与默认请求。

修改源码后重新生成 ZIP：

```powershell
.\.venv\Scripts\python.exe scripts\package_skill.py
.\.venv\Scripts\python.exe -m pyflakes skill\paper-translate-package\scripts
```

技能初版经过 48 项合成小样的前向检查，涵盖有/无补充材料、模板变化、字段解析、缺页/篡改拦截、续作和 ZIP 完整性。该检查不代表长论文翻译语义已自动验证。修改技能后按真实目标任务复核，再在客户端更新已导入的技能；ZIP 不会自动覆盖所有人的本地安装。

## 六、提交改动的流程

```powershell
git switch -c codex/your-feature
# 编辑并运行与修改相关的检查
git add <确认需要提交的文件>
git commit -m "Describe the change"
git push -u origin codex/your-feature
```

在 GitHub 创建 Pull Request，写清问题、修改后的行为、验证结果和数据迁移影响。取得写权限前也可先在自己的本地分支开发。

新 Python 模块必须有中文模块文档字符串，写明作用、依赖、被谁调用和扩展点；公共类/函数用中文说明。修 bug 补 `tests/test_regressions.py`，改动结构时更新 `planning/` 对应文档。不要把虚拟环境、运行锁、日志、个人库或账号凭据提交。

## 七、已知待改进点

- 文件名相似度配对阈值为 0.88，可能把标题相近论文合并；预览会提醒核对，尚无手动拆分/重配。
- 导入 `build_plan` 仍在界面线程运行，大量文件时可能暂时等待。
- 中文标题排序按字符码点，未按拼音排序。
- 单实例锁尚无自动化覆盖。FieldService 未加查询缓存，修改时需考虑备份恢复后的失效。

这些是后续开发方向，不应在仅修文档或性能优化时顺带改变现有行为。
