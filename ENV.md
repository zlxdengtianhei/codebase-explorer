# ENV — codebase-explorer/.venv

- **归属**：`adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer`（MCP server + skill，代码库结构分析与文档生成）。
- **Python 版本**：3.13.11（`.python-version`）。**部分有记录**：`pyproject.toml` 显式钉 `requires-python = ">=3.12,<3.14"`（`INSTALL.md` 亦要求 `Python >= 3.12`）；上界 `<3.14` 的具体原因未写明（推测是 graph-sitter / tree-sitter 系编译轮子当时未覆盖 3.14），勿轻易突破这个上界。
- **依赖声明**：本目录已有 `pyproject.toml` + `uv.lock`（完整锁定，与当前 `.venv` 一致，未发现缺项），故不新增 `requirements.txt`。
- **重建**：
  ```
  uv venv --python 3.13.11 .venv && uv sync
  ```
  （`uv sync` 读取本目录的 `pyproject.toml`/`uv.lock`；命令形态已在 scratchpad 用等价合成项目实测跑通，未用本目录真实依赖图重跑。）
- **本目录 `.venv` 是可回收缓存**：删了照上面命令重建即可。
