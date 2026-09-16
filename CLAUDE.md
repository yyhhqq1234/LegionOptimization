# CLAUDE.md — Claude Code Working Notes

> 本仓 canonical agent 指令在 **`AGENTS.md`** ——动手前先完整读它（铁律/门禁/Done 定义都在那边，本文件不再重复）。
> 两文件冲突时以 `AGENTS.md` 为准。

## Claude 专属约定

1. 默认中文回复；代码标识符英文，注释/文档可用中文。
2. 超过 3 个文件的改动先用 plan mode 列计划，用户确认后再写。
3. 每个 commit 前跑 `pytest tests/`（P3 落盘前以“无测试可跑”显式声明代替）。
4. 不主动 push 到公开远端之外的任何地方；`origin master` 按既定流程可推，禁止 force-push。
5. 读文件用 Read 工具，不用 shell cat；找文件用 Glob，不用 shell find（仓库卫生 + 审计要求）。
6. 验收证据贴文件路径 + commit，不贴“我认为通过了”。
7. 本地私有即 ignore（AGENTS.md 铁律 10）：在仓内新增本地私有内容（实测 CSV/log/照片、个人路径、
   secrets、临时副本、`*.local.*`/`private/` 类）后，必须先补 `.gitignore` 并用 `git status --porcelain`
   确认无私有文件再 commit；`artifacts/` 实测大文件与照片类大二进制永不进仓。
8. 双机分工（AGENTS.md 铁律 11）：A = 主力开发机，B = 副开发机（兼验证+迁移目标）；
   B 机可领独立模块/复测/文档活，细则见 `docs/machine-registry.md` §7；动同一文件先通气，
   push 前先 `git pull --rebase`。
