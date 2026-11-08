# 项目协作约定

## 用户和范围

- 用通俗中文交流。仅审查时不改代码；仅优化时不改变功能；重大功能改动先给方案确认。
- 分层为 `ui → services → storage → core`，`importers` 只依赖 `core`。遵循 `planning/` 中的模块与注释规范。
- 新 Python 模块和公共接口写中文说明；修 bug 在 `tests/test_regressions.py` 补回归测试，结构变动同步文档。

## 持续同步 GitHub（用户已授权）

用户最新确认 **GIGI-666 和 livcheng666 都属于自己，项目继续使用 GIGI-666**。唯一目标私有仓库为 `https://github.com/GIGI-666/litmgr`。不再向 livcheng666 转移。浏览器与命令行可能分别登录这两个账号，不能仅凭浏览器的空仓库列表就判断上传失败或更换仓库所有者。

用户要求：以后完成文献管理系统或论文翻译技能的修改后，都提交并同步至上述目标仓库，同时更新文献库新增论文和其他业务数据。无需在每次正常同步前重复请求许可。保持仓库私有；不自动邀请协作者或更改访问权限。

完成相关任务时：

1. 检查 Git 状态和远程分支，保留他人的未提交工作，不混入与本次无关的改动。远端写入前用 `gh api user` 等确认实际授权身份与用户确认的目标账号一致；当前应为 GIGI-666，origin 应为 `https://github.com/GIGI-666/litmgr.git`。不一致时报告具体情况，不擅自转移仓库或删除任何账号的访问权限。
2. 程序有代码修改时运行 `pytest -q` 和 `pyflakes litmgr tests`；技能脚本或分享工具有修改时也做相应验证。Windows 离屏测试设置 `QT_QPA_PLATFORM=offscreen`、`QT_QPA_FONTDIR=C:/Windows/Fonts`、`QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu`。
3. 技能以仓库 `skill/paper-translate-package/` 提供可编辑版本，修改后用 `scripts/package_skill.py` 重建 ZIP。若本机已安装在 `C:/Users/GIGI/.codex/skills/paper-translate-package/`，核对变更来源后同步这两份源码，避免将旧版覆盖新版；更新使用说明中的行为变化。
4. 查明本次实际使用的文献库。原维护者本机通常为 `D:/2file/研究生2026.9.7/文献库`，配置在 `LITMGR_HOME/config.json` 或 `%APPDATA%/litmgr/config.json`；换机器后不要把这个绝对路径当作必需目录。使用 `scripts/snapshot_library.py` 从真实库只读生成新快照，核验后更新仓库 `shared_library/`，包括数据库、已有关联文件、历史备份和可移植设置。不要把仓库旧快照反向覆盖用户实际使用的库。
5. 更新快照时保留原始文件字节，遵守 `.gitattributes`；排除运行锁、WAL/SHM/journal、日志、缓存、虚拟环境和凭据。只修改新生成的分享副本，不重写原论文文件。递归移动/删除前先核对绝对路径，仅操作本任务创建且位于预期目录的副本。
6. 若论文数、文件数或字段数改变，同步 README 的快照概况及必要教程。检查快照清单与 Git 实际入库字节哈希一致。
7. 提交并正常推送到 `origin`。当前默认分支为 `master`；用户指定分支/PR 流程时按其要求，不强制推送，不覆盖远端协作者提交。若远程账号、地址或权限不符，先报告具体情况。
8. 推送后核对远端提交和关键文件，明确说明代码、技能、数据各自是否已同步。若实际库不可访问或未保存输入无法取得，不声称已更新全部数据，也不要用空库替代已有快照。

此约定是在代理完成任务时同步，不会让桌面程序在无人操作时持续自动上传。用户单独新增论文后发“同步文献库”也按上述流程执行；不得擅自安装常驻监控或定时自动上传任务。

## 开发入口

- 安装、使用和协作者访问：`README.md`。
- 分层、数据、测试、技能维护：`DEVELOPMENT.md`。
- 模块、迁移、运行维护：`planning/03_模块清单.md`、`planning/02_数据库设计.md`、`planning/06_运行与维护说明.md`。
