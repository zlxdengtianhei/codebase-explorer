# Phase 5: Semantic Reorganization — Complete Design

> **Status**: Design document for Phase 5 implementation.
> **Date**: 2026-03-24
> **Input references**:
> - `optimization_prompts/results/02b_skill_design_v2.md` Section 6.5
> - `optimization_prompts/results/03_final_progressive_scheme.md` Section 2.4
> - `.agents/skills/codebase-explorer/SKILL.md` Phase 4 section

---

## 1. Phase 5 Overview

Phase 5 (Semantic Reorganization) is the bridge between Phase 4's mechanical INDEX assembly and Phase 6's automated validation. Its purpose is to transform a flat, algorithm-derived document structure into a semantically coherent, hierarchical documentation architecture.

**Core principle**: "Generate first, reorganize later." Phase 3 generates DETAIL documents per original feature cone. Phase 4 assembles initial INDEX documents and a flat `doc-manifest.json`. Phase 5 then reads all generated content and applies semantic judgment to produce the final document organization.

**Why this phase exists**: The dependency graph parser cannot resolve all relationships (e.g., cross-package imports, dynamic dispatch, configuration-based routing). This produces many "orphan cones" -- for example, Flask's 54 cones include 50 single-file cones. Mechanically merging by directory name is semantically incorrect (`tests/test_basic.py` and `tests/test_json.py` test different subsystems despite sharing a directory). Only an LLM that has read the actual DETAIL content can make correct reorganization decisions.

---

## 2. Entry and Exit Conditions

### 2.1 Entry Conditions (Phase 4 Completion Flags)

Phase 5 begins when ALL of the following are true:

| Condition | How to check |
|-----------|--------------|
| All Phase 3 DETAIL tasks are `"complete"` in `state.json` | `state.json.tasks[*].status == "complete"` for all tasks where `type in ("batch", "single", "split")` |
| All Phase 4 INDEX tasks are `"complete"` in `state.json` | `state.json.tasks["index_assembly"].status == "complete"` |
| `doc-manifest.json` exists and is valid JSON | File exists at `.codebase-docs/doc-manifest.json` with `version` field present |
| `doc-manifest.json` has `details` and `groups` fields | Both top-level keys exist and are non-empty objects |
| At least one batch INDEX.md exists in `.codebase-docs/` | At least one `groups[*].index_path` file exists on disk |
| All `details[*].path` files in manifest exist on disk | File existence check for every path in `doc-manifest.json.details` |

**Failure mode**: If any condition is not met, Phase 5 MUST NOT start. Log the specific failing condition and return control to the Skill orchestrator for retry or user notification.

### 2.2 Exit Conditions (Phase 5 Completion Flags)

Phase 5 is complete when ALL of the following are true:

| Condition | How to verify |
|-----------|---------------|
| `doc-manifest.json` has been updated to final version | `doc-manifest.json.status == "final"` |
| Root `INDEX.md` has been regenerated | `.codebase-docs/INDEX.md` exists and `last_modified > phase_5_start_time` |
| Every `details[*].path` in manifest exists on disk | File existence check passes for all entries |
| Every `groups[*].index_path` in manifest exists on disk | File existence check passes for all group INDEX files |
| No `details[*].group` references a non-existent group | Referential integrity: all `group` values exist as keys in `groups` |
| All `groups[*].detail_ids` reference existing detail entries | Referential integrity: all detail IDs exist as keys in `details` |
| `operations_log` in manifest is non-empty (or explicitly `[]` for no-op) | Field exists, documenting what Phase 5 did (even if nothing) |

---

## 3. doc-manifest.json Complete Schema

### 3.1 Initial Version (Phase 4 Output -- Flat Structure)

Phase 4 produces the initial `doc-manifest.json` with a flat group structure. All details are assigned to top-level groups; no nesting exists yet.

```json
{
  "version": "2.1",
  "status": "initial",
  "project_id": "9b425a3ed56f",
  "root_index": ".codebase-docs/INDEX.md",
  "created_at": "2026-03-24T10:00:00Z",
  "updated_at": "2026-03-24T10:00:00Z",

  "details": {
    "<detail_id>": {
      "path": ".codebase-docs/<group>/<DETAIL_filename>.md",
      "source_files": ["<source_file_path_1>", "<source_file_path_2>"],
      "units": ["<source_file_path_1>", "<source_file_path_2>"],
      "tokens": 1200,
      "group": "<group_id>"
    }
  },

  "groups": {
    "<group_id>": {
      "name": "<Human Readable Group Name>",
      "index_path": ".codebase-docs/<group>/INDEX.md",
      "parent": null,
      "detail_ids": ["<detail_id_1>", "<detail_id_2>"],
      "subgroups": []
    }
  },

  "operations_log": []
}
```

**Key characteristics of the initial version**:
- `status` is `"initial"`
- All `groups[*].parent` values are `null` (flat, no hierarchy)
- All `groups[*].subgroups` arrays are empty
- `operations_log` is an empty array

### 3.2 Final Version (Phase 5 Output -- Hierarchical Structure)

After Phase 5 completes, the manifest is updated with hierarchical grouping, operation history, and a `"final"` status marker.

```json
{
  "version": "2.1",
  "status": "final",
  "project_id": "9b425a3ed56f",
  "root_index": ".codebase-docs/INDEX.md",
  "created_at": "2026-03-24T10:00:00Z",
  "updated_at": "2026-03-24T12:30:00Z",

  "details": {
    "flask-tests-test_basic": {
      "path": ".codebase-docs/test-suite/DETAIL_test_basic.md",
      "source_files": ["flask/tests/test_basic.py"],
      "units": ["flask/tests/test_basic.py"],
      "tokens": 1200,
      "group": "test-suite"
    },
    "flask-tests-test_blueprints": {
      "path": ".codebase-docs/test-suite/DETAIL_test_blueprints.md",
      "source_files": ["flask/tests/test_blueprints.py"],
      "units": ["flask/tests/test_blueprints.py"],
      "tokens": 800,
      "group": "test-suite"
    },
    "test-app-cliapp": {
      "path": ".codebase-docs/test-suite/test-apps/DETAIL_cliapp.md",
      "source_files": [
        "flask/tests/test_apps/cliapp/app.py",
        "flask/tests/test_apps/cliapp/factory.py"
      ],
      "units": [
        "flask/tests/test_apps/cliapp/app.py",
        "flask/tests/test_apps/cliapp/factory.py"
      ],
      "tokens": 600,
      "group": "test-apps"
    },
    "tutorial-blog-feature": {
      "path": ".codebase-docs/tutorial/DETAIL_blog.md",
      "source_files": [
        "flask/examples/tutorial/flaskr/blog.py",
        "flask/examples/tutorial/flaskr/db.py"
      ],
      "units": [
        "flask/examples/tutorial/flaskr/blog.py",
        "flask/examples/tutorial/flaskr/db.py"
      ],
      "tokens": 1800,
      "group": "tutorial"
    },
    "tutorial-auth": {
      "path": ".codebase-docs/auth/DETAIL_tutorial_auth.md",
      "source_files": ["flask/examples/tutorial/flaskr/auth.py"],
      "units": ["flask/examples/tutorial/flaskr/auth.py"],
      "tokens": 900,
      "group": "auth-module"
    }
  },

  "groups": {
    "test-suite": {
      "name": "Test Suite",
      "index_path": ".codebase-docs/test-suite/INDEX.md",
      "parent": null,
      "detail_ids": ["flask-tests-test_basic", "flask-tests-test_blueprints"],
      "subgroups": ["test-apps"]
    },
    "test-apps": {
      "name": "Test Applications",
      "index_path": ".codebase-docs/test-suite/test-apps/INDEX.md",
      "parent": "test-suite",
      "detail_ids": ["test-app-cliapp"],
      "subgroups": []
    },
    "tutorial": {
      "name": "Tutorial Example",
      "index_path": ".codebase-docs/tutorial/INDEX.md",
      "parent": null,
      "detail_ids": ["tutorial-blog-feature"],
      "subgroups": []
    },
    "auth-module": {
      "name": "Authentication Module",
      "index_path": ".codebase-docs/auth/INDEX.md",
      "parent": null,
      "detail_ids": ["tutorial-auth"],
      "subgroups": []
    }
  },

  "operations_log": [
    {
      "operation_id": "op_001",
      "type": "split",
      "timestamp": "2026-03-24T11:15:00Z",
      "agent": "reorg-level-0-tutorial",
      "detail_id": "tutorial-blog-feature",
      "extract_units": ["flask/examples/tutorial/flaskr/auth.py"],
      "new_detail_id": "tutorial-auth",
      "to_group": "auth-module",
      "reason": "auth.py implements user authentication independent of blog CRUD logic"
    },
    {
      "operation_id": "op_002",
      "type": "create_group",
      "timestamp": "2026-03-24T11:16:00Z",
      "agent": "reorg-level-0-tutorial",
      "group_id": "auth-module",
      "name": "Authentication Module",
      "reason": "Split auth.py from tutorial needs a dedicated group"
    },
    {
      "operation_id": "op_003",
      "type": "move",
      "timestamp": "2026-03-24T11:45:00Z",
      "agent": "reorg-root",
      "detail_id": "tutorial-auth",
      "from_group": "tutorial",
      "to_group": "auth-module",
      "reason": "Authentication is a cross-cutting concern, not tutorial-specific"
    }
  ]
}
```

### 3.3 Schema Field Differences: Initial vs Final

| Field | Initial (Phase 4) | Final (Phase 5) |
|-------|-------------------|-----------------|
| `status` | `"initial"` | `"final"` |
| `updated_at` | Phase 4 completion time | Phase 5 completion time |
| `groups[*].parent` | Always `null` | May be non-null (nested groups) |
| `groups[*].subgroups` | Always `[]` | May contain group IDs |
| `operations_log` | `[]` | Array of operation records (may still be `[]` if no changes needed) |
| `details` entries | Original Phase 3 DETAIL mapping | May have new entries (from split), removed entries (from merge), or updated paths/groups (from move) |
| `groups` entries | Original Phase 4 groups only | May have new groups (from create_group) or removed groups (from dissolve) |

### 3.4 Schema Validation Rules

```python
# Referential integrity checks for doc-manifest.json
def validate_manifest(manifest):
    errors = []

    # 1. Every detail.group must reference an existing group
    for detail_id, detail in manifest["details"].items():
        if detail["group"] not in manifest["groups"]:
            errors.append(f"detail {detail_id} references non-existent group {detail['group']}")

    # 2. Every group.detail_ids entry must reference an existing detail
    for group_id, group in manifest["groups"].items():
        for did in group["detail_ids"]:
            if did not in manifest["details"]:
                errors.append(f"group {group_id} references non-existent detail {did}")

    # 3. Every group.subgroups entry must reference an existing group
    for group_id, group in manifest["groups"].items():
        for sg in group["subgroups"]:
            if sg not in manifest["groups"]:
                errors.append(f"group {group_id} references non-existent subgroup {sg}")

    # 4. Parent-child consistency
    for group_id, group in manifest["groups"].items():
        if group["parent"] is not None:
            parent = manifest["groups"].get(group["parent"])
            if parent is None:
                errors.append(f"group {group_id} has non-existent parent {group['parent']}")
            elif group_id not in parent["subgroups"]:
                errors.append(f"group {group_id} claims parent {group['parent']} but is not in parent's subgroups")

    # 5. No circular parent references
    for group_id in manifest["groups"]:
        visited = set()
        current = group_id
        while current is not None:
            if current in visited:
                errors.append(f"circular parent chain detected starting from {group_id}")
                break
            visited.add(current)
            current = manifest["groups"].get(current, {}).get("parent")

    # 6. detail.units must be a subset of detail.source_files
    for detail_id, detail in manifest["details"].items():
        if not set(detail["units"]).issubset(set(detail["source_files"])):
            errors.append(f"detail {detail_id}: units not subset of source_files")

    return errors
```

---

## 4. @unit Marking: Parsing and Usage Rules in Phase 5

### 4.1 @unit Writing Rules (Phase 3 DETAIL Agent -- recap)

The @unit markers are written by Phase 3 DETAIL Agents. The rules below are reproduced from 02b Section 4 to ensure Phase 5's parsing is consistent.

**When to write @unit markers**: Only when `file_count > 1` for the cone (multi-file cones). Single-file cones do NOT have @unit markers; the entire DETAIL is an atomic, unsplittable unit.

**@unit marker format**:

```markdown
<!-- @unit: {filepath} | tokens: {estimated_tokens} -->
### {filename} -- short description

...documentation content for this source file...

<!-- @/unit: {filepath} -->
```

**Structural rules**:
- The `<!-- @unit: ... -->` opening tag and `<!-- @/unit: ... -->` closing tag form a fenced region
- `{filepath}` is the relative path from project root (e.g., `flask/examples/tutorial/flaskr/auth.py`)
- `tokens` is the approximate token count of the enclosed content (chars / 4)
- The `## 功能概述` section is placed BEFORE all @unit blocks (at file top)
- The `## 设计决策` and `## 在系统中的位置` sections are placed AFTER all @unit blocks (at file bottom)
- These outer sections are NOT part of any @unit and must be regenerated after split/merge operations

### 4.2 @unit Parsing Rules in Phase 5

Phase 5 Reorganization INDEX Agents parse @unit markers to identify splittable segments. The parsing algorithm:

```python
import re

def parse_units(detail_content: str) -> list[dict]:
    """Parse @unit markers from a DETAIL.md file.

    Returns a list of unit records, each containing:
    - filepath: str (the source file path)
    - tokens: int (estimated token count)
    - content: str (the text between opening and closing markers, inclusive)
    - start_offset: int (character offset of opening marker)
    - end_offset: int (character offset of end of closing marker)
    """
    pattern = re.compile(
        r'(<!-- @unit: (?P<filepath>[^\|]+?)\s*\|\s*tokens:\s*(?P<tokens>\d+)\s*-->)'
        r'(?P<content>.*?)'
        r'(<!-- @/unit: (?P=filepath)\s*-->)',
        re.DOTALL
    )

    units = []
    for match in pattern.finditer(detail_content):
        units.append({
            "filepath": match.group("filepath").strip(),
            "tokens": int(match.group("tokens")),
            "content": match.group(0),  # full match including markers
            "start_offset": match.start(),
            "end_offset": match.end(),
        })
    return units
```

**Parsing constraints**:
- Opening and closing @unit tags MUST have matching filepaths (the regex enforces this via backreference)
- Nested @unit markers are NOT supported (a @unit block cannot contain another @unit block)
- Content outside all @unit blocks is considered "global sections" (功能概述, 设计决策, 在系统中的位置)
- If a DETAIL has no @unit markers, it is treated as an atomic unit (single-file cone) -- Phase 5 cannot split it

### 4.3 @unit Usage Rules in Phase 5 Operations

| Operation | How @unit is used |
|-----------|-------------------|
| **Move** | Entire DETAIL (with all its @unit blocks) is moved. No @unit parsing needed. |
| **Merge** | All @unit blocks from source DETAILs are concatenated into the target DETAIL. Original @unit markers are preserved. |
| **Split** | Specific @unit blocks are extracted from a DETAIL by matching filepath. The extracted @unit content (including markers) is placed in a new DETAIL. The original DETAIL's global sections (功能概述, 设计决策) must be regenerated by the LLM for both the reduced original and the new file. |
| **Create Group** | Does not interact with @unit markers directly. |

**Invariant**: Phase 5 NEVER creates, deletes, or modifies the content within @unit markers. It only moves @unit blocks between DETAIL files. The @unit content remains exactly as Phase 3 DETAIL Agents wrote it.

---

## 5. The Four Operations: Precise Rules and Flask Examples

### 5.1 Operation: Move

**Definition**: Transfer an entire DETAIL document from one group to another.

**When to use**: A DETAIL is semantically misplaced in its current group. The INDEX Agent judges that the DETAIL's functionality belongs to a different group based on its content.

**Preconditions**:
- The target group must already exist (or be created first via Create Group)
- The DETAIL's `group` field in manifest matches its current physical location

**Execution steps**:

1. Read `doc-manifest.json`
2. Move file on disk: `mv .codebase-docs/<old-group>/DETAIL_x.md .codebase-docs/<new-group>/DETAIL_x.md`
3. Update manifest:
   - `details["x"].group = "<new-group>"`
   - `details["x"].path = ".codebase-docs/<new-group>/DETAIL_x.md"`
   - Remove `"x"` from `groups["<old-group>"].detail_ids`
   - Add `"x"` to `groups["<new-group>"].detail_ids`
4. Update internal relative links in the moved DETAIL (e.g., `../INDEX.md` paths change based on new depth)
5. Append operation record to `operations_log`

**Flask example -- Moving a JSON test to the json-serialization group**:

Before:
```
.codebase-docs/
├── test-suite/
│   ├── INDEX.md
│   ├── DETAIL_test_basic.md
│   ├── DETAIL_test_json.md          <-- tests JSON serialization
│   └── DETAIL_test_blueprints.md
├── json-serialization/
│   ├── INDEX.md
│   ├── DETAIL_json_init.md
│   └── DETAIL_json_provider.md
```

The Reorganization INDEX Agent reads `DETAIL_test_json.md` and determines it tests the JSON serialization subsystem (it imports `flask.json.provider` and tests `JSONProvider.dumps()`/`JSONProvider.loads()`). It is semantically part of the json-serialization group.

Operation record:
```json
{
  "operation_id": "op_010",
  "type": "move",
  "timestamp": "2026-03-24T11:20:00Z",
  "agent": "reorg-level-0-test-suite",
  "detail_id": "flask-tests-test_json",
  "from_group": "test-suite",
  "to_group": "json-serialization",
  "reason": "DETAIL_test_json.md tests JSONProvider serialization/deserialization, semantically belongs with JSON subsystem"
}
```

After:
```
.codebase-docs/
├── test-suite/
│   ├── INDEX.md                     (regenerated, removed test_json link)
│   ├── DETAIL_test_basic.md
│   └── DETAIL_test_blueprints.md
├── json-serialization/
│   ├── INDEX.md                     (regenerated, added test_json link)
│   ├── DETAIL_json_init.md
│   ├── DETAIL_json_provider.md
│   └── DETAIL_test_json.md          <-- moved here
```

### 5.2 Operation: Merge

**Definition**: Combine multiple small DETAIL documents that describe aspects of the same functionality into a single DETAIL.

**When to use**: Multiple DETAILs in the same group are semantically redundant or describe tightly coupled sub-features that a reader would always want to see together. Typical trigger: two or more DETAILs with < 500 tokens each in the same group.

**Preconditions**:
- All source DETAILs must be in the same group (or first Move them to the same group)
- Combined token count must not exceed 8000 tokens (readability limit)
- Each source DETAIL's @unit markers must not overlap in filepath

**Execution steps**:

1. Read all source DETAIL files
2. Create merged DETAIL:
   - Concatenate all @unit blocks (preserving each @unit's markers and content)
   - Have the LLM write a new `## 功能概述` section covering the combined functionality
   - Merge `source_files` and `units` arrays (union, deduplicated)
   - Sum token counts
3. Write merged DETAIL to the group directory with a new descriptive filename
4. Delete the original DETAIL files from disk
5. Update manifest:
   - Create new detail entry with merged data
   - Remove old detail entries
   - Update group's `detail_ids` (remove old IDs, add new ID)
6. Append operation record to `operations_log`

**Flask example -- Merging CLI app test fixtures**:

Before:
```
.codebase-docs/test-suite/test-apps/
├── INDEX.md
├── DETAIL_cliapp_app.md       (300 tokens, documents cliapp/app.py)
└── DETAIL_cliapp_factory.md   (250 tokens, documents cliapp/factory.py)
```

The Reorganization INDEX Agent observes that both files together form a single CLI test app fixture. `cliapp/app.py` defines the app instance and `cliapp/factory.py` provides the factory function; they are always used together.

Merged DETAIL (`DETAIL_cliapp.md`):
```markdown
# CLI App Test Fixture

## 功能概述

Flask CLI 测试应用提供了一个最小化的 Flask 应用实例和对应的工厂函数，用于 CLI 命令行工具的集成测试。两个文件协同工作：app.py 提供静态实例，factory.py 提供可配置的工厂方法。

<!-- @unit: flask/tests/test_apps/cliapp/app.py | tokens: 200 -->
## app.py -- CLI test app instance

### 核心接口
- `app = Flask(__name__)` -- 最小化 Flask 应用实例

### 内部逻辑
1. 创建一个无额外配置的 Flask 实例
2. 注册一个简单的 `/` 路由用于健康检查
<!-- @/unit: flask/tests/test_apps/cliapp/app.py -->

<!-- @unit: flask/tests/test_apps/cliapp/factory.py | tokens: 180 -->
## factory.py -- CLI test app factory

### 核心接口
- `create_app(info=None) -> Flask` -- 工厂函数，返回配置好的 Flask 实例

### 内部逻辑
1. 接受可选的 `ScriptInfo` 参数
2. 返回与 app.py 相同的应用实例，但支持动态配置
<!-- @/unit: flask/tests/test_apps/cliapp/factory.py -->

## 设计决策

CLI 测试 fixture 将静态实例和工厂函数分离为两个文件，是因为 Flask CLI 的 `--app` 参数支持两种加载模式：直接引用模块属性（app.py:app）和调用工厂函数（factory.py:create_app）。
```

Operation record:
```json
{
  "operation_id": "op_020",
  "type": "merge",
  "timestamp": "2026-03-24T11:35:00Z",
  "agent": "reorg-level-0-test-apps",
  "detail_ids": ["test-app-cliapp-app", "test-app-cliapp-factory"],
  "new_detail_id": "test-app-cliapp",
  "new_name": "CLI App Test Fixture",
  "reason": "Two files jointly form CLI test fixture, always used together (550 tokens combined)"
}
```

### 5.3 Operation: Split

**Definition**: Extract one or more @unit blocks from an existing DETAIL into a new DETAIL, typically in a different group.

**When to use**: A multi-file DETAIL contains @unit blocks that are semantically independent from the rest. The INDEX Agent identifies that a specific @unit belongs to a different functional domain.

**Preconditions**:
- The source DETAIL must have @unit markers (multi-file cone)
- The @unit to extract must be identifiable by filepath
- After extraction, both the original and new DETAIL must have at least one @unit or be a valid single-file DETAIL

**Execution steps**:

1. Read the source DETAIL file
2. Locate the @unit block(s) to extract using `<!-- @unit: {filepath}` and `<!-- @/unit: {filepath} -->` markers
3. Extract the matched content (including markers)
4. Write new DETAIL:
   - Include extracted @unit block(s)
   - LLM writes a new `## 功能概述` section for the extracted content
   - LLM writes a new `## 设计决策` section
   - Set `source_files` and `units` to only the extracted file paths
5. Update source DETAIL:
   - Remove the extracted @unit block(s)
   - LLM rewrites the `## 功能概述` section (it may no longer be accurate)
   - Update `## 设计决策` if it referenced the extracted files
6. Update manifest:
   - Create new detail entry for the extracted content
   - Update original detail entry (remove extracted units from `source_files` and `units`, reduce `tokens`)
   - Assign new detail to target group
7. Append operation record to `operations_log`

**Flask example -- Splitting auth.py from tutorial blog feature**:

Before -- `DETAIL_blog_feature.md` in the `tutorial` group:
```markdown
# Tutorial Blog Feature

## 功能概述

Flask 教程中的博客应用实现，包含博客文章的 CRUD 操作、用户认证和数据库初始化功能。三个模块协同工作构成完整的 Web 应用教程示例。

<!-- @unit: flask/examples/tutorial/flaskr/blog.py | tokens: 944 -->
## blog.py -- 博客路由与视图

### 核心接口
- `create()` -- 创建新文章
- `update(id)` -- 更新文章
- `delete(id)` -- 删除文章
- `index()` -- 文章列表页

### 内部逻辑
1. 通过 `auth.login_required` 装饰器验证用户身份
2. 使用 `db.get_db()` 获取数据库连接
3. 对每个操作执行 SQL 查询并返回渲染结果
<!-- @/unit: flask/examples/tutorial/flaskr/blog.py -->

<!-- @unit: flask/examples/tutorial/flaskr/auth.py | tokens: 941 -->
## auth.py -- 用户认证

### 核心接口
- `register()` -- 用户注册视图
- `login()` -- 用户登录视图
- `logout()` -- 用户登出视图
- `login_required(view)` -- 认证装饰器
- `load_logged_in_user()` -- 请求前钩子

### 内部逻辑
1. 使用 `werkzeug.security` 的密码哈希函数
2. 将用户 ID 存储在 session 中
3. `login_required` 装饰器检查 `g.user` 是否存在
<!-- @/unit: flask/examples/tutorial/flaskr/auth.py -->

<!-- @unit: flask/examples/tutorial/flaskr/db.py | tokens: 515 -->
## db.py -- 数据库初始化

### 核心接口
- `get_db()` -- 获取当前请求的数据库连接
- `close_db(e=None)` -- 关闭数据库连接
- `init_db()` -- 执行 schema.sql 初始化表结构
- `init_app(app)` -- 注册数据库相关的 teardown 和 CLI 命令

### 内部逻辑
1. 使用 SQLite 作为数据库后端
2. 数据库连接存储在 `g` 对象中（请求级别生命周期）
<!-- @/unit: flask/examples/tutorial/flaskr/db.py -->

## 设计决策

教程将认证、博客和数据库分为三个独立模块，演示 Flask 的 Blueprint 组织模式。auth 模块提供 `login_required` 装饰器供 blog 模块使用，db 模块提供底层数据访问。
```

The Root INDEX Agent observes that `auth.py` implements a general-purpose authentication system that could be referenced by other codebase components beyond the tutorial. It decides to split auth.py into its own group.

After split -- source DETAIL (`DETAIL_blog.md`, updated):
```markdown
# Tutorial Blog Feature

## 功能概述

Flask 教程中的博客应用实现，包含博客文章的 CRUD 操作和数据库初始化功能。blog.py 提供路由和视图逻辑，db.py 提供底层数据库访问。

<!-- @unit: flask/examples/tutorial/flaskr/blog.py | tokens: 944 -->
## blog.py -- 博客路由与视图
...（unchanged）
<!-- @/unit: flask/examples/tutorial/flaskr/blog.py -->

<!-- @unit: flask/examples/tutorial/flaskr/db.py | tokens: 515 -->
## db.py -- 数据库初始化
...（unchanged）
<!-- @/unit: flask/examples/tutorial/flaskr/db.py -->

## 设计决策

教程博客模块依赖外部认证模块（参见 [auth/DETAIL_tutorial_auth.md](../auth/DETAIL_tutorial_auth.md)）提供用户身份验证，db 模块提供底层数据访问。
```

After split -- new DETAIL (`auth/DETAIL_tutorial_auth.md`):
```markdown
# Tutorial 认证模块

## 功能概述

Flask 教程中的用户认证实现，提供注册、登录、登出功能和 `login_required` 装饰器。该模块可被教程中的其他视图模块引用以实现访问控制。

<!-- @unit: flask/examples/tutorial/flaskr/auth.py | tokens: 941 -->
## auth.py -- 用户认证
...（content moved verbatim from original）
<!-- @/unit: flask/examples/tutorial/flaskr/auth.py -->

## 设计决策

认证模块使用 Flask session 机制管理用户状态，通过装饰器模式（`login_required`）为其他视图提供统一的访问控制接口。
```

Operation record:
```json
{
  "operation_id": "op_030",
  "type": "split",
  "timestamp": "2026-03-24T12:00:00Z",
  "agent": "reorg-root",
  "detail_id": "tutorial-blog-feature",
  "extract_units": ["flask/examples/tutorial/flaskr/auth.py"],
  "new_detail_id": "tutorial-auth",
  "to_group": "auth-module",
  "reason": "auth.py implements standalone authentication that blog.py and other modules depend on; semantically independent from blog CRUD"
}
```

### 5.4 Operation: Create Group / Dissolve Group

**Create Group Definition**: Establish a new group directory with an INDEX.md, typically to house DETAILs moved or split from other groups.

**When to use**: A semantic cluster of DETAILs emerges that does not fit any existing group. Or a split operation produces a new DETAIL that needs a home.

**Create Group execution steps**:

1. Create directory: `mkdir .codebase-docs/<new-group>/`
2. LLM writes a new `INDEX.md` for the group
3. Update manifest:
   - Add new group entry with `parent`, `detail_ids`, `subgroups`
   - If this is a subgroup, update parent's `subgroups` array
4. Append operation record to `operations_log`

**Dissolve Group Definition**: Remove a group that has become empty or too small to justify its own section. Transfer all remaining DETAILs to the parent group.

**Dissolve Group execution steps**:

1. Move all DETAILs in the dissolving group to its parent group (using Move operations)
2. Transfer any subgroups to the parent group
3. Delete the group's INDEX.md and directory
4. Update manifest:
   - Remove group entry
   - Update parent's `subgroups` (remove dissolved group, add its former subgroups)
   - All transferred detail entries get updated `group` and `path`
5. Append operation record to `operations_log`

**Flask example -- Creating a subgroup for test applications**:

The Reorganization INDEX Agent processing the `test-suite` group notices that several DETAILs document test helper applications (not actual tests). It creates a subgroup:

Before:
```
.codebase-docs/test-suite/
├── INDEX.md
├── DETAIL_test_basic.md
├── DETAIL_test_blueprints.md
├── DETAIL_cliapp_app.md        <-- test helper app
├── DETAIL_cliapp_factory.md    <-- test helper app
└── DETAIL_blueprintapp.md      <-- test helper app
```

After:
```
.codebase-docs/test-suite/
├── INDEX.md                    (regenerated, links to test-apps subgroup)
├── DETAIL_test_basic.md
├── DETAIL_test_blueprints.md
└── test-apps/
    ├── INDEX.md                (new, documents test helper apps)
    ├── DETAIL_cliapp.md        (merged from cliapp_app + cliapp_factory)
    └── DETAIL_blueprintapp.md  (moved from parent)
```

Operation record:
```json
{
  "operation_id": "op_040",
  "type": "create_group",
  "timestamp": "2026-03-24T11:50:00Z",
  "agent": "reorg-level-0-test-suite",
  "group_id": "test-apps",
  "name": "Test Applications",
  "parent": "test-suite",
  "reason": "Test helper apps (cliapp, blueprintapp) serve as fixtures, not actual test assertions; separating them improves navigation"
}
```

---

## 6. Reorganization INDEX Agent Complete Prompt Template

```
# Semantic Reorganization Task — {{group_name}}

## Your Role

You are the Reorganization INDEX Agent for the **{{group_name}}** group.
Your responsibility is to review all DETAIL documents assigned to this group,
evaluate their semantic coherence, and reorganize them if needed.

You can read DETAIL content but you MUST NOT read source code files.
You operate on documentation structure, not on code.

## Current Document Manifest

```json
{{current_manifest}}
```

## Batch INDEX Context

The following INDEX documents provide the current organizational structure:

{{batch_index_content}}

## DETAIL Files in Your Group

{{#each detail_files}}
### {{detail_id}} ({{tokens}} tokens, {{unit_count}} units)

**Source files:** {{source_files_list}}

**功能概述 (first paragraph):**
{{first_paragraph}}

**@unit list:**
{{#each units}}
- `{{filepath}}` ({{tokens}} tokens)
{{/each}}
{{/each}}

## Sibling Groups (for context)

{{#each sibling_groups}}
- **{{group_name}}** ({{detail_count}} details): {{brief_description}}
{{/each}}

## Your Task

Analyze the DETAIL documents in your group and determine if reorganization is needed.

### Decision Criteria

1. **Semantic Misplacement**: Does any DETAIL describe functionality that clearly belongs
   to a sibling group? A DETAIL about JSON serialization testing should be in the
   json-serialization group, not the test-suite group.

2. **Redundant Small DETAILs**: Are there multiple DETAILs under 500 tokens that describe
   aspects of the same logical feature? Merge candidates must be in the same group and
   their combined tokens must not exceed 8000.

3. **Cross-Domain @units**: Does any multi-file DETAIL contain @unit blocks where some
   units belong to a completely different functional domain? For example, a tutorial DETAIL
   containing both blog.py and auth.py where auth.py is a standalone authentication module.

4. **Missing Subgroup Structure**: Are there 5+ DETAILs that share a common sub-theme
   (e.g., all test helper applications) that would benefit from a subgroup?

### Decision Priority

1. Do NOT reorganize unless there is a clear semantic reason
2. Prefer Move over Split (simpler operation)
3. Prefer Merge only when both DETAILs are very small (< 500 tokens each)
4. Create subgroups only when there are 3+ DETAILs that clearly belong together
5. Algorithm constraints are inviolable: never merge past 8000 tokens combined

## Output Format

Output a reorganization plan as JSON:

```json
{
  "group": "{{group_id}}",
  "analysis": "Brief 2-3 sentence analysis of the group's current state",
  "operations": [
    {
      "type": "move",
      "detail_id": "<detail_id>",
      "to_group": "<target_group_id>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "merge",
      "detail_ids": ["<id1>", "<id2>"],
      "new_name": "<merged document title>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "split",
      "detail_id": "<detail_id>",
      "extract_units": ["<filepath1>"],
      "to_group": "<target_group_id>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "create_group",
      "group_id": "<new_group_id>",
      "name": "<Human Readable Name>",
      "parent": "<parent_group_id or null>",
      "reason": "<1-2 sentence justification>"
    }
  ]
}
```

If no reorganization is needed, output:
```json
{
  "group": "{{group_id}}",
  "analysis": "All DETAILs are semantically coherent within this group. No changes needed.",
  "operations": []
}
```

## Execution Instructions

After outputting the plan, execute it:

1. **Create Group** operations first (target groups must exist before Move/Split)
2. **Split** operations second (creates new DETAILs that may need moving)
3. **Move** operations third (moves existing and newly split DETAILs)
4. **Merge** operations last (after all moves are done, merge within final groups)
5. After ALL operations: update `doc-manifest.json` with all changes
6. Regenerate this group's INDEX.md to reflect the new structure

## Constraints (NON-NEGOTIABLE)

- Do NOT add, delete, or modify content within @unit markers
- Only move @unit blocks between DETAIL files during Split operations
- After every Split or Merge, regenerate the affected DETAIL's `## 功能概述` section
- Keep @unit internal content exactly as Phase 3 DETAIL Agents wrote it
- Update `doc-manifest.json` after each operation to maintain consistency
- Do NOT read source code files — work only with DETAIL documents
- Do NOT create @unit markers that did not exist in Phase 3 output
- Combined token count for Merge must not exceed 8000
- Every DETAIL must belong to exactly one group after all operations

## Style Constraints (Same as All Agents)

1. Language: 中文 for prose sections, English for technical terms/signatures
2. Headers: ## for sections, ### for subsections. No #### or deeper.
3. Mermaid: Use `graph TD`, valid identifiers, max 15 nodes
4. No opinions: Describe facts only
5. No first person: Use third person or imperative
```

### Template Variable Injection Reference

| Variable | Source | Description |
|----------|--------|-------------|
| `{{group_name}}` | `manifest.groups[group_id].name` | Human-readable name of the group being processed |
| `{{group_id}}` | Loop variable | Machine ID of the group being processed |
| `{{current_manifest}}` | `doc-manifest.json` file content | Full JSON content of the current manifest state |
| `{{batch_index_content}}` | Read from `groups[*].index_path` files | Concatenated content of all batch INDEX.md files from Phase 4 |
| `{{detail_files}}` | For each `detail_id` in `groups[group_id].detail_ids`: read DETAIL, parse @units | Array of detail metadata including first paragraph, unit list, token counts |
| `{{detail_id}}` | Key from `manifest.details` | Machine ID of each DETAIL in the group |
| `{{tokens}}` | `manifest.details[detail_id].tokens` | Token count of the DETAIL |
| `{{unit_count}}` | `len(manifest.details[detail_id].units)` | Number of @unit blocks in the DETAIL |
| `{{source_files_list}}` | `manifest.details[detail_id].source_files` | Comma-separated source file paths |
| `{{first_paragraph}}` | Parsed from DETAIL file's `## 功能概述` section | First 2-3 sentences of the DETAIL |
| `{{units}}` | Parsed via @unit regex from DETAIL file | Array of `{filepath, tokens}` from @unit markers |
| `{{sibling_groups}}` | All groups where `parent == this_group.parent` and `group_id != this_group_id` | Context about peer groups for Move decisions |

---

## 7. Bottom-Up Hierarchical Processing Order

### 7.1 Level Definition

The processing order is determined by the group hierarchy depth:

```
Level N (deepest):  Leaf groups with no subgroups
Level N-1:          Groups whose only children are Level N groups
...
Level 1:            Groups whose parent is the root
Level 0:            Root INDEX Agent (generates final INDEX.md)
```

### 7.2 Level Calculation Algorithm

```python
def calculate_group_levels(manifest: dict) -> dict[str, int]:
    """Calculate processing level for each group.

    Returns dict mapping group_id -> level (0 = root, higher = deeper).
    Processing order is from highest level to lowest.
    """
    groups = manifest["groups"]

    # Find max depth for each group
    def depth(group_id: str) -> int:
        group = groups[group_id]
        if not group["subgroups"]:
            return 0
        return 1 + max(depth(sg) for sg in group["subgroups"])

    # Root groups (parent=null) get depth relative to their subtree
    root_groups = [gid for gid, g in groups.items() if g["parent"] is None]

    levels = {}
    max_depth = 0
    for root_id in root_groups:
        d = depth(root_id)
        max_depth = max(max_depth, d)

    # Assign levels: leaf groups get max_depth, root groups get their depth from root
    def assign_levels(group_id: str, current_depth: int):
        levels[group_id] = current_depth
        for sg in groups[group_id]["subgroups"]:
            assign_levels(sg, current_depth + 1)

    for root_id in root_groups:
        assign_levels(root_id, 0)

    return levels
```

### 7.3 Processing Sequence

```
Step 1: Identify all groups and calculate levels
Step 2: Sort groups by level DESCENDING (deepest first)
Step 3: For each level (deepest to shallowest):
    a. Spawn Reorganization INDEX Agent for each group at this level (parallel within level)
    b. Each agent reads its group's DETAILs and sibling context
    c. Each agent outputs and executes reorganization plan
    d. Wait for all agents at this level to complete
    e. Merge manifest updates (conflict resolution: later writes win for same field)
Step 4: Root INDEX Agent (Level 0):
    a. Read updated manifest (reflecting all lower-level changes)
    b. Evaluate cross-group reorganization needs
    c. Generate final .codebase-docs/INDEX.md
    d. Set manifest.status = "final"
    e. Write final doc-manifest.json
```

### 7.4 Why Bottom-Up?

Bottom-up processing ensures that:

1. **Leaf groups stabilize first**: The deepest groups have the most localized scope and can reorganize independently
2. **Parent agents see clean state**: When a parent-level agent runs, all its children have already been reorganized
3. **Cross-group moves propagate upward**: If Level N moves a DETAIL to a sibling, the Level N-1 agent sees the updated structure and can decide whether further moves are needed
4. **Root agent has global view**: The final Root INDEX Agent sees the fully reorganized structure and can make global decisions (e.g., dissolving empty groups, creating new top-level groupings)

### 7.5 Flask Example -- Processing Order

Given the Flask document hierarchy after Phase 4:

```
Level 0: root (generates INDEX.md)
├── test-suite          (Level 0 top-level group)
│   └── test-apps       (Level 1 subgroup)
├── tutorial            (Level 0 top-level group)
├── core-runtime        (Level 0 top-level group)
├── request-handling    (Level 0 top-level group)
├── json-serialization  (Level 0 top-level group)
├── cli                 (Level 0 top-level group)
└── sansio              (Level 0 top-level group)
```

Processing order:
1. **Level 1** (deepest): `test-apps` agent runs first -- merges small fixture DETAILs, no cross-group operations possible at this level
2. **Level 0** (all top-level groups, parallel): `test-suite`, `tutorial`, `core-runtime`, `request-handling`, `json-serialization`, `cli`, `sansio` agents run in parallel -- each evaluates its DETAILs, may propose moves to sibling groups
3. **Root Agent**: Reads final manifest, generates root INDEX.md, evaluates whether any cross-group structural changes are needed, writes final manifest

---

## 8. doc-manifest.json State Transition Rules (flat to hierarchical)

### 8.1 State Machine

```
┌──────────────────────────────────────────────────────────────────┐
│                     doc-manifest.json States                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Phase 4 Output        Phase 5 Processing         Phase 5 Done   │
│  ┌──────────┐         ┌──────────────────┐       ┌──────────┐    │
│  │ "initial" │────────→│ "reorganizing"   │──────→│ "final"  │    │
│  │           │         │                  │       │          │    │
│  │ flat      │         │ iterative updates│       │ hierarchy│    │
│  │ no parent │         │ add parents      │       │ stable   │    │
│  │ no subgrp │         │ add subgroups    │       │ verified │    │
│  │ ops_log=[]│         │ ops_log grows    │       │ ops_log  │    │
│  └──────────┘         └──────────────────┘       └──────────┘    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Transition Rules

**Transition 1: initial -> reorganizing**

Trigger: Phase 5 starts processing the first group.

Changes:
- `status` changes from `"initial"` to `"reorganizing"`
- `updated_at` is set to current timestamp

**Transition 2: reorganizing -> reorganizing (iterative)**

Trigger: Each Reorganization INDEX Agent completes and writes its changes.

Changes (cumulative):
- New entries may appear in `details` (from Split operations)
- Entries may be removed from `details` (from Merge operations)
- `details[*].group` and `details[*].path` may change (from Move operations)
- New entries may appear in `groups` (from Create Group operations)
- Entries may be removed from `groups` (from Dissolve operations)
- `groups[*].parent` may change from `null` to a group ID
- `groups[*].subgroups` may gain new entries
- `operations_log` grows with each operation
- `updated_at` is updated after each agent completes

**Transition 3: reorganizing -> final**

Trigger: Root INDEX Agent completes processing and writes the final INDEX.md.

Changes:
- `status` changes from `"reorganizing"` to `"final"`
- `updated_at` is set to current timestamp
- Root INDEX.md is written/updated
- All group INDEX.md files are regenerated to reflect final structure

### 8.3 Conflict Resolution

When multiple agents at the same level operate in parallel and both modify the manifest:

1. **Read-before-write**: Each agent reads the current manifest state at the start of its execution
2. **Atomic writes**: Each agent writes its manifest updates atomically (write to `.tmp`, then `os.replace`)
3. **Sequential within level**: If parallel agents at the same level produce conflicting manifest changes, the Skill orchestrator applies them sequentially in a deterministic order (alphabetical by group_id)
4. **No cross-group conflicts**: Agents at the same level operate on disjoint sets of DETAILs (their own group's `detail_ids`), so data-level conflicts should not occur. The exception is Move operations that target sibling groups -- these are applied after all agents at the level have generated their plans, before any agent executes.

### 8.4 Invariants That Must Hold at Every State

These conditions must be true after every manifest update:

1. Every `detail.group` value references a valid `groups` key
2. Every ID in `groups[*].detail_ids` references a valid `details` key
3. Every ID in `groups[*].subgroups` references a valid `groups` key
4. No circular parent chains exist
5. Union of all `groups[*].detail_ids` equals the set of all `details` keys (every detail is in exactly one group)
6. Every `details[*].path` file exists on disk
7. Every `groups[*].index_path` file exists on disk (after the group's INDEX is regenerated)

---

## 9. Root INDEX Agent Special Responsibilities

The Root INDEX Agent runs last (Level 0, after all group-level agents). It has additional responsibilities beyond the standard Reorganization prompt:

1. **Global architecture overview**: Generate the final `.codebase-docs/INDEX.md` with:
   - Project title and description
   - Mermaid dependency diagram at the group level
   - Feature list with summaries (from SNIPPET files)
   - Architecture layers breakdown
   - Cross-cutting concerns identification

2. **Empty group cleanup**: Dissolve any groups that ended up with 0 DETAILs after lower-level reorganization

3. **Top-level grouping assessment**: Determine if any top-level groups should be merged or if a new meta-group should be created

4. **Final manifest write**: Set `status: "final"` and ensure all invariants hold

5. **Link regeneration**: Ensure all relative links in the root INDEX.md correctly point to the reorganized structure

---

## 10. Summary of Data Flow

```
Phase 4 Output                     Phase 5 Processing                    Phase 5 Output
─────────────                     ─────────────────                     ──────────────

DETAIL.md files ─────────────────→ Reorganization INDEX Agents ────────→ Reorganized DETAIL files
(with @unit markers)                (read DETAIL content)                 (moved/merged/split)

Batch INDEX.md files ────────────→ Reorganization INDEX Agents ────────→ Regenerated group INDEX files
(Phase 4 initial)                   (context for decisions)

doc-manifest.json ───────────────→ Reorganization INDEX Agents ────────→ doc-manifest.json (final)
(status: "initial", flat)           (iterative updates)                   (status: "final", hierarchical)

                                    Root INDEX Agent ──────────────────→ .codebase-docs/INDEX.md (final)
                                    (global view, last to run)
```

---

## 11. Error Handling

### 11.1 Agent Failure

If a Reorganization INDEX Agent fails mid-execution:
- `doc-manifest.json` may be in an inconsistent state (partially applied operations)
- **Recovery**: Re-read the `operations_log` to determine which operations completed. Roll back incomplete operations by restoring files from the previous state (or re-run Phase 4 INDEX assembly to reset to `"initial"` state).

### 11.2 @unit Parsing Failure

If a DETAIL file has malformed @unit markers (mismatched opening/closing tags):
- The agent MUST NOT attempt to split that DETAIL
- Log a warning and treat the DETAIL as an atomic unit (same as single-file cone)
- Record the issue in `operations_log` with `type: "warning"`

### 11.3 Token Budget Violation

If a Merge operation would exceed 8000 tokens:
- The agent MUST NOT execute the merge
- Consider alternative: keep as separate DETAILs within the same group, or create a subgroup with an OVERVIEW instead

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **DETAIL** | A documentation file describing one or more source files in depth. Contains @unit markers for multi-file cones. |
| **@unit** | An HTML comment fence (`<!-- @unit: ... -->` / `<!-- @/unit: ... -->`) demarcating a source-file-specific section within a DETAIL. |
| **Group** | A logical collection of related DETAILs, represented as a directory with an INDEX.md. |
| **Manifest** | `doc-manifest.json` -- the Single Source of Truth for document organization. |
| **Reorganization INDEX Agent** | The LLM agent responsible for evaluating and executing semantic reorganization within a group. |
| **Root INDEX Agent** | The final agent that generates the top-level INDEX.md and finalizes the manifest. |
| **Level** | The depth of a group in the hierarchy. Level 0 = top-level groups, higher = deeper nesting. |
| **Flat structure** | All groups at the same level, no parent-child relationships (Phase 4 output). |
| **Hierarchical structure** | Groups with parent-child nesting (Phase 5 output). |
