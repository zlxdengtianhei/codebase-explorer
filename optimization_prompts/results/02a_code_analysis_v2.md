# 代码分析架构优化 V2

> 本文档由代码分析深度审查产出，供 V2 实现参考。
> 基于对实际源代码（`src/parser/codebase.py`, `src/graph/dependency.py`, `src/graph/grouper.py`）的精确读取，
> 以及 V1 架构文档（`01_current_architecture.md`）、核心需求（`00_vision_and_requirements.md`）、
> V1 优化提案（`01_code_analysis_architecture.md`）的综合分析。

---

## 1. V1→V2 改进摘要

| V1 中的问题 / 不清晰点 | V2 的修正与澄清 |
|---|---|
| V1 提案中用 `func.calls` 字段引用函数调用信息 | 实际字段名是 `FunctionInfo.calls: tuple[str, ...]`，存储的是**被调用函数的名称字符串**，不是文件路径 |
| V1 未说明 `func.dependencies` 的语义 | 实际字段是 `FunctionInfo.dependencies: tuple[str, ...]`，存储的是**依赖文件的绝对路径** |
| V1 假设 `class.base_classes` 是文件路径 | 实际是**类名字符串**（如 `"App"`），需要二次查找才能解析到文件路径 |
| V1 假设 `file.import_sources` 是模块名 | 实际已是**解析后的绝对文件路径**（graph-sitter 在解析时已完成 resolve） |
| V1 中 `dependency.py` 只合并 import 边 + function.dependencies，未区分边类型 | 当前实现将所有边合并为通用权重计数，丢失了 import/call/inherit 的语义区别 |
| V1 中 Louvain 被用作主力分组工具 | V2 明确：Louvain 降级为 fallback，仅用于扁平目录场景；主力是 Feature Cone 算法 |
| V1 未给出 SCC 内文件如何分配 cone 的决策规则 | V2 提供完整的 SCC cone 归属决策算法 |
| V1 的 5 个输出文件 schema 只有字段名，无示例值 | V2 给出包含真实示例值的完整 JSON schema |
| V1 的装箱算法描述模糊 | V2 给出可直接实现的伪代码 |
| V1 未处理"项目无纯入口点（库代码）"的情况 | V2 明确定义 fallback：以 in-degree 最低的节点集合作为 Feature Root |

---

## 2. graph-sitter API 可行性验证

### 2.1 精确字段名（来自 `src/parser/codebase.py` 实际代码）

#### `FileInfo`（第 33-41 行）

```python
@dataclass(frozen=True)
class FileInfo:
    filepath: str                   # 绝对路径
    language: str                   # "python" | "typescript" | "javascript"
    line_count: int
    function_names: tuple[str, ...] # 文件内函数名列表（名称字符串，非对象）
    class_names: tuple[str, ...]    # 文件内类名列表（名称字符串，非对象）
    import_sources: tuple[str, ...] # 已解析的被导入文件绝对路径列表
```

**关键事实**：`import_sources` 在 `_extract_file`（第 204-213 行）中通过以下逻辑生成：
```python
for imp in getattr(sf, "imports", []):
    resolved = getattr(imp, "resolved_symbol", None)
    if resolved is not None:
        rf = getattr(resolved, "file", None)
        if rf is not None:
            import_sources.append(str(rf.filepath))
```
即：**只收录成功 resolve 的 import**（有对应文件的 local import）。外部库（stdlib、third-party）被丢弃，因为它们没有对应的本地文件路径。

#### `FunctionInfo`（第 43-52 行）

```python
@dataclass(frozen=True)
class FunctionInfo:
    name: str
    filepath: str                     # 函数所在文件的绝对路径
    start_line: int
    end_line: int
    parameters: tuple[str, ...]
    return_type: str | None
    calls: tuple[str, ...]            # 被调用函数的名称字符串（如 "create_app"）
    dependencies: tuple[str, ...]     # 依赖文件的绝对路径（跨文件）
```

**关键区分**：
- `calls` = 被调用函数的**名称**（需要通过 `name→file` 查找表才能解析到文件）
- `dependencies` = 已解析的**文件路径**（graph-sitter 分析出的文件级依赖）

`calls` 在 `_extract_function`（第 229-233 行）生成：
```python
for call in getattr(fn, "function_calls", []):
    fd = getattr(call, "function_definition", None)
    if fd is not None:
        calls.append(fd.name)
```

`dependencies` 在 `_extract_function`（第 234-238 行）生成：
```python
for dep in getattr(fn, "dependencies", []):
    dp = getattr(dep, "filepath", None)
    if dp is not None:
        deps.append(str(dp))
```

#### `ClassInfo`（第 54-63 行）

```python
@dataclass(frozen=True)
class ClassInfo:
    name: str
    filepath: str                     # 类所在文件的绝对路径
    start_line: int
    end_line: int
    methods: tuple[str, ...]
    base_classes: tuple[str, ...]     # 父类名称字符串（如 "App"，非文件路径！）
    subclasses: tuple[str, ...]
```

**关键事实**：`base_classes` 在 `_extract_class`（第 256-257 行）中是从 `cl.superclasses` 获取的：
```python
supers = getattr(cl, "superclasses", None)
base_classes = tuple(b.name for b in supers) if supers is not None else ()
```
存储的是**类名字符串**，不是文件路径。需要通过 `class_name→file` 查找表才能建立继承边。

### 2.2 跨文件函数调用图可行性

**可行性结论**：可以通过两个路径建立跨文件调用边。

**路径 A（推荐）**：使用 `func.dependencies` 字段
- 这已经是解析好的文件路径，可直接用于建图
- 但语义是"该函数依赖的文件"，不仅仅是被调用的函数所在的文件
- 当前 `dependency.py` 已经使用了这个字段（第 99-104 行）

**路径 B（精确但需额外查找）**：使用 `func.calls`（函数名）+ 构建 `name→file` 查找表
- 先构建 `func_name_to_file: dict[str, str] = {f.name: f.filepath for f in snapshot.functions}`
- 然后对每个 `call_name in func.calls`，查找 `func_name_to_file.get(call_name)`
- 问题：函数名在不同文件中可能重名（如各文件都有 `__init__`）
- 解决：查找表只保留唯一名称，重名函数的调用边丢弃（保守策略）

**回退策略**：当 graph-sitter 无法解析某引用时：
1. `func.dependencies` 为空列表 → 该函数贡献零边
2. `func.calls` 中的名称在查找表中找不到 → 跳过该边
3. 外部库调用 → 完全忽略（它们不是项目内文件）
4. 最终退化为纯 import 边的图，等同于当前实现

### 2.3 继承边可行性

**构建继承边的步骤**：
1. 预建 `class_name_to_file: dict[str, str] = {c.name: c.filepath for c in snapshot.classes}`
2. 对每个 `ClassInfo cls`，对每个 `base_name in cls.base_classes`：
   - 查找 `base_file = class_name_to_file.get(base_name)`
   - 若 `base_file` 存在且 `base_file != cls.filepath`，则添加继承边 `cls.filepath → base_file`
3. 重名类问题同函数：采用保守策略，重名时跳过

---

## 3. 完整算法设计

### 3.1 加权多关系图构建（含伪代码）

```python
def build_weighted_multi_relation_graph(snapshot: CodebaseSnapshot) -> nx.DiGraph:
    """
    构建加权多关系有向图，整合 import、函数调用、继承三种关系。

    边权语义：
      import 边：weight += 1（基础关联）
      call 边：  weight += 2（运行时依赖，比 import 更紧密）
      inherit 边：weight += 3（行为继承，最紧密的语义关联）

    同一对文件之间的多种关系：权重累加。
    例：app.py → sansio/app.py 同时有 import+call+inherit = weight 6
    """
    G = nx.DiGraph()

    # Step 1: 构建查找表
    file_set = {fi.filepath for fi in snapshot.files}

    # 函数名 → 文件路径（仅唯一名称）
    func_name_count: dict[str, int] = defaultdict(int)
    for func in snapshot.functions:
        func_name_count[func.name] += 1
    func_name_to_file: dict[str, str] = {
        func.name: func.filepath
        for func in snapshot.functions
        if func_name_count[func.name] == 1  # 只保留唯一名称
    }

    # 类名 → 文件路径（仅唯一名称）
    class_name_count: dict[str, int] = defaultdict(int)
    for cls in snapshot.classes:
        class_name_count[cls.name] += 1
    class_name_to_file: dict[str, str] = {
        cls.name: cls.filepath
        for cls in snapshot.classes
        if class_name_count[cls.name] == 1
    }

    # Step 2: 添加节点
    for fi in snapshot.files:
        G.add_node(fi.filepath,
                   language=fi.language,
                   line_count=fi.line_count,
                   function_count=len(fi.function_names),
                   class_count=len(fi.class_names))

    # Step 3: 累积边权重
    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    edge_types: dict[tuple[str, str], set[str]] = defaultdict(set)

    # 来源1：import 边（weight=1）
    for fi in snapshot.files:
        src = fi.filepath
        for target in fi.import_sources:
            if target in file_set and target != src:
                edge_weights[(src, target)] += 1
                edge_types[(src, target)].add("import")

    # 来源2：函数调用边（通过 func.dependencies，weight=2）
    # func.dependencies 已是文件路径，直接使用
    for func in snapshot.functions:
        src = func.filepath
        for dep_path in func.dependencies:
            if dep_path in file_set and dep_path != src:
                edge_weights[(src, dep_path)] += 2
                edge_types[(src, dep_path)].add("call")

    # 来源3：继承边（通过 class.base_classes 名称→文件查找，weight=3）
    for cls in snapshot.classes:
        src = cls.filepath
        for base_name in cls.base_classes:
            base_file = class_name_to_file.get(base_name)
            if base_file and base_file in file_set and base_file != src:
                edge_weights[(src, base_file)] += 3
                edge_types[(src, base_file)].add("inherit")

    # Step 4: 将累积权重写入图
    for (src, tgt), weight in edge_weights.items():
        types = sorted(edge_types[(src, tgt)])
        G.add_edge(src, tgt, weight=weight, edge_types=types)

    return G
```

**多重关系处理决策**：当同一对文件 (A, B) 之间同时存在 import、call、inherit 三种关系时，**累加权重**（而非取最大值或建多条边）。这样 Louvain 算法和 SCC 分析都能看到完整的关联强度。例如 `app.py → sansio/app.py` 若同时有三种关系则 weight=6，Louvain 不会轻易将其分开。

**无法解析的引用处理**：
- 外部库 import → 不出现在 `import_sources` 中（已由 graph-sitter 过滤）
- 函数名重名 → 跳过（保守策略，不建错误边）
- 类名重名 → 跳过（同上）
- graph-sitter 解析失败的文件 → 该文件贡献零边（但节点保留）

### 3.2 SCC 强连通分量识别

```python
def compute_sccs(G: nx.DiGraph) -> tuple[nx.DiGraph, dict[str, str]]:
    """
    识别 SCC 并返回压缩后的 DAG 和文件→SCC节点的映射。

    Returns:
        condensed_dag: SCC 压缩后的有向无环图
        file_to_scc_node: {文件路径 → SCC节点ID字符串}
    """
    # nx.condensation 返回 SCC 压缩后的 DAG
    # 每个节点是一个 SCC，包含 'members' 属性（文件路径集合）
    condensed = nx.condensation(G)

    # 构建文件 → SCC节点 的映射
    file_to_scc_node: dict[str, str] = {}
    scc_node_to_files: dict[str, list[str]] = {}

    for scc_node_id in condensed.nodes():
        members = list(condensed.nodes[scc_node_id]['members'])

        # 为 SCC 节点生成人类可读的 ID
        if len(members) == 1:
            scc_id = members[0]  # 单文件 SCC，直接用文件路径
        else:
            # 多文件 SCC：使用公共目录前缀 + "::scc"
            common = os.path.commonpath(members)
            scc_id = f"{common}::scc_{scc_node_id}"

        scc_node_to_files[scc_id] = members
        for f in members:
            file_to_scc_node[f] = scc_id

    # 重建以可读 ID 为节点的 DAG
    readable_dag = nx.DiGraph()
    for scc_id, members in scc_node_to_files.items():
        readable_dag.add_node(scc_id, members=members, is_scc=(len(members) > 1))

    for u, v in condensed.edges():
        u_id = file_to_scc_node[list(condensed.nodes[u]['members'])[0]]
        v_id = file_to_scc_node[list(condensed.nodes[v]['members'])[0]]
        if u_id != v_id:
            readable_dag.add_edge(u_id, v_id)

    return readable_dag, file_to_scc_node
```

### 3.3 DAG 分层（纵向结构）

```python
def compute_dag_layers(dag: nx.DiGraph) -> dict[str, int]:
    """
    计算每个 SCC 节点的层级（最长路径深度）。

    层级定义：
      layer(node) = 0  如果没有前驱节点（被谁依赖）→ 最高层（用户/入口）
      layer(node) = max(layer(pred) + 1 for pred in predecessors)

    注意：这里"predecessors"指"依赖该节点的文件"，即上层使用者。
    layer=0 的节点是被最多人使用的"顶层入口"。

    实际上 DAG 的层级方向：
      顶层（layer 高）= 功能入口（views.py, cli.py）
      底层（layer 低）= 基础实现（scaffold.py, helpers.py）

    我们采用"最长路径"定义：
      layer(node) = max path length from node to any sink
      sink = 出度为0的节点（没有依赖的文件，如底层库包装）
    """
    # 拓扑排序
    topo_order = list(nx.topological_sort(dag))

    layer: dict[str, int] = {node: 0 for node in dag.nodes()}

    # 从 sink 反向计算（到 sink 的距离）
    for node in reversed(topo_order):
        successors = list(dag.successors(node))
        if successors:
            layer[node] = max(layer[s] for s in successors) + 1

    return layer
```

**层级语义**（以 Flask 为例）：
- `layer=0`：叶子节点，无依赖，如 `sansio/scaffold.py`（纯基础实现）
- `layer=1`：依赖底层，如 `sansio/app.py`
- `layer=2`：核心门面，如 `[app.py+ctx.py+globals.py]::scc`（SCC 节点）
- `layer=3`：功能入口，如 `views.py`, `cli.py`, `testing.py`

### 3.4 功能锥体提取（横向功能分组）

#### Step 1: 确定 Feature Root（功能入口）

```python
def find_feature_roots(dag: nx.DiGraph) -> list[str]:
    """
    找出功能入口节点（Feature Root）。

    定义：DAG 中入度为 0 的节点（没有任何内部代码依赖它）。

    处理"无纯入口"的库代码情况（例如 Flask 本身）：
    - 若没有入度为 0 的节点，则取最小入度的节点集合作为 Feature Root
    - 取入度 <= min_in_degree + 1 的所有节点
    """
    in_degrees = dict(dag.in_degree())

    roots = [node for node, deg in in_degrees.items() if deg == 0]

    if not roots:
        # 库代码 fallback：入度最小的节点集
        min_deg = min(in_degrees.values())
        roots = [node for node, deg in in_degrees.items() if deg <= min_deg + 1]

    return roots
```

#### Step 2: 追踪依赖锥体（BFS/DFS）

```python
def extract_feature_cones(
    dag: nx.DiGraph,
    roots: list[str],
    shared_threshold: int = 2
) -> dict[str, FeatureCone]:
    """
    从每个 Feature Root 向依赖方向追踪，标记文件的归属。

    shared_threshold: 一个节点被 N 个以上的 cone 共享时，标记为"基础设施"
    决策依据：threshold=2 意味着一旦被超过1个功能使用，就归为共享基础设施。
    这比 threshold=3 更保守，避免把实际的共享代码错误归入某单一功能。
    """
    # 每个节点归属的 cone 集合
    node_cones: dict[str, set[str]] = defaultdict(set)

    for root in roots:
        cone_name = root  # 以入口节点路径为 cone 标识
        # BFS 追踪所有依赖（successors = 被依赖的节点）
        visited = set()
        queue = [root]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            node_cones[node].add(cone_name)
            for successor in dag.successors(node):
                if successor not in visited:
                    queue.append(successor)

    # 分类：专属 vs 共享
    cones: dict[str, FeatureCone] = {}
    infrastructure_nodes: set[str] = set()

    for node, belonging_cones in node_cones.items():
        if len(belonging_cones) >= shared_threshold:
            infrastructure_nodes.add(node)

    for root in roots:
        exclusive = []
        shared_refs = []
        for node, belonging_cones in node_cones.items():
            if root in belonging_cones:
                if node in infrastructure_nodes:
                    shared_refs.append(node)
                else:
                    exclusive.append(node)

        cones[root] = FeatureCone(
            cone_id=root,
            entry_point=root,
            exclusive_files=exclusive,
            shared_deps=shared_refs
        )

    return cones, infrastructure_nodes
```

**共享阈值决策**：选用 `threshold=2`（被 2 个以上的 cone 共享即归为基础设施）。理由：
- Flask 中 `app.py` 被 `views.py`, `cli.py`, `testing.py` 共同依赖 → 归为 Core 基础设施，正确
- `wrappers.py` 只被 `views.py` 依赖 → 归为请求处理功能的专属代码，正确
- threshold=3 会让太多文件保留在单功能内，使功能分组边界不清晰

#### Step 3: SCC 节点的锥体归属

```python
def assign_scc_to_cone(
    scc_node: str,
    scc_members: list[str],
    cones: dict[str, FeatureCone]
) -> str:
    """
    决定一个 SCC（多文件强连通分量）归属哪个 cone。

    策略：SCC 成员中，哪个 cone 包含最多成员 → SCC 归属该 cone。
    若 SCC 被多个 cone 平均分享 → 标记为基础设施（infrastructure）。

    例：app.py+ctx.py+globals.py 组成的 SCC，若都被 views+cli 共享 → 基础设施
    """
    cone_member_count: dict[str, int] = defaultdict(int)
    for member in scc_members:
        for cone_id, cone in cones.items():
            if member in cone.exclusive_files:
                cone_member_count[cone_id] += 1

    if not cone_member_count:
        return "infrastructure"

    max_count = max(cone_member_count.values())
    winners = [c for c, n in cone_member_count.items() if n == max_count]

    if len(winners) == 1:
        return winners[0]
    else:
        return "infrastructure"  # 平局 → 基础设施
```

---

## 4. 5 个 JSON 输出文件完整 Schema

### 4.1 `01_structure.json`：原始代码结构

```json
{
  "schema_version": "2.0",
  "project_root": "/Users/user/projects/flask",
  "generated_at": "2026-03-23T10:00:00Z",
  "languages": ["python"],
  "total_files": 24,
  "total_lines": 15432,
  "total_functions": 287,
  "total_classes": 42,
  "files": [
    {
      "path": "/Users/user/projects/flask/src/flask/app.py",
      "relative_path": "src/flask/app.py",
      "language": "python",
      "line_count": 1234,
      "char_count": 45678,
      "estimated_tokens": 13051,
      "function_names": ["create_app", "make_response", "send_file"],
      "class_names": ["Flask"],
      "import_sources": [
        "/Users/user/projects/flask/src/flask/globals.py",
        "/Users/user/projects/flask/src/flask/ctx.py",
        "/Users/user/projects/flask/src/flask/sansio/app.py"
      ]
    },
    {
      "path": "/Users/user/projects/flask/src/flask/sansio/app.py",
      "relative_path": "src/flask/sansio/app.py",
      "language": "python",
      "line_count": 867,
      "char_count": 31200,
      "estimated_tokens": 8914,
      "function_names": ["_check_setup_finished", "add_url_rule"],
      "class_names": ["App"],
      "import_sources": [
        "/Users/user/projects/flask/src/flask/sansio/scaffold.py"
      ]
    }
  ],
  "functions": [
    {
      "name": "create_app",
      "filepath": "/Users/user/projects/flask/src/flask/app.py",
      "start_line": 45,
      "end_line": 89,
      "parameters": ["import_name", "instance_path"],
      "return_type": "Flask",
      "calls": ["_check_setup_finished", "register_blueprint"],
      "dependencies": [
        "/Users/user/projects/flask/src/flask/globals.py",
        "/Users/user/projects/flask/src/flask/ctx.py"
      ]
    }
  ],
  "classes": [
    {
      "name": "Flask",
      "filepath": "/Users/user/projects/flask/src/flask/app.py",
      "start_line": 100,
      "end_line": 800,
      "methods": ["__init__", "run", "test_client", "register_blueprint"],
      "base_classes": ["App"],
      "subclasses": []
    }
  ],
  "weighted_edges": [
    {
      "source": "/Users/user/projects/flask/src/flask/app.py",
      "target": "/Users/user/projects/flask/src/flask/sansio/app.py",
      "weight": 6,
      "edge_types": ["import", "call", "inherit"]
    },
    {
      "source": "/Users/user/projects/flask/src/flask/views.py",
      "target": "/Users/user/projects/flask/src/flask/app.py",
      "weight": 1,
      "edge_types": ["import"]
    }
  ],
  "external_references_skipped": 47
}
```

**字段说明**：
- `char_count`：原始字符数，用于更精确的 token 估算（`char_count / 4`）
- `estimated_tokens`：`char_count / 4`（Python），精度优于行数×系数
- `weighted_edges`：三种关系合并后的边列表，`weight` 是累加值
- `external_references_skipped`：graph-sitter 未能解析的外部引用计数

### 4.2 `02_dag.json`：SCC 压缩后的 DAG 与层级分配

```json
{
  "schema_version": "2.0",
  "project_root": "/Users/user/projects/flask",
  "generated_at": "2026-03-23T10:01:00Z",
  "scc_count": 4,
  "dag_node_count": 18,
  "dag_edge_count": 22,
  "max_layer": 3,
  "sccs": [
    {
      "scc_id": "/Users/user/projects/flask/src/flask::scc_0",
      "members": [
        "/Users/user/projects/flask/src/flask/app.py",
        "/Users/user/projects/flask/src/flask/ctx.py",
        "/Users/user/projects/flask/src/flask/globals.py"
      ],
      "is_multi_file_scc": true,
      "internal_cycle_reason": "app.py ↔ ctx.py ↔ globals.py 相互导入"
    }
  ],
  "nodes": [
    {
      "node_id": "/Users/user/projects/flask/src/flask::scc_0",
      "is_scc": true,
      "members": [
        "/Users/user/projects/flask/src/flask/app.py",
        "/Users/user/projects/flask/src/flask/ctx.py",
        "/Users/user/projects/flask/src/flask/globals.py"
      ],
      "layer": 2,
      "in_degree": 3,
      "out_degree": 1,
      "total_lines": 2890,
      "total_estimated_tokens": 24650
    },
    {
      "node_id": "/Users/user/projects/flask/src/flask/views.py",
      "is_scc": false,
      "members": ["/Users/user/projects/flask/src/flask/views.py"],
      "layer": 3,
      "in_degree": 0,
      "out_degree": 2,
      "total_lines": 345,
      "total_estimated_tokens": 2940
    },
    {
      "node_id": "/Users/user/projects/flask/src/flask/sansio/scaffold.py",
      "is_scc": false,
      "members": ["/Users/user/projects/flask/src/flask/sansio/scaffold.py"],
      "layer": 0,
      "in_degree": 2,
      "out_degree": 0,
      "total_lines": 512,
      "total_estimated_tokens": 4360
    }
  ],
  "edges": [
    {
      "source": "/Users/user/projects/flask/src/flask/views.py",
      "target": "/Users/user/projects/flask/src/flask::scc_0",
      "weight": 3
    },
    {
      "source": "/Users/user/projects/flask/src/flask::scc_0",
      "target": "/Users/user/projects/flask/src/flask/sansio/app.py",
      "weight": 6
    }
  ],
  "layers": {
    "0": ["/Users/user/projects/flask/src/flask/sansio/scaffold.py"],
    "1": ["/Users/user/projects/flask/src/flask/sansio/app.py"],
    "2": ["/Users/user/projects/flask/src/flask::scc_0"],
    "3": [
      "/Users/user/projects/flask/src/flask/views.py",
      "/Users/user/projects/flask/src/flask/cli.py",
      "/Users/user/projects/flask/src/flask/testing.py",
      "/Users/user/projects/flask/src/flask/blueprints.py"
    ]
  }
}
```

### 4.3 `03_feature_cones.json`：功能分组

```json
{
  "schema_version": "2.0",
  "project_root": "/Users/user/projects/flask",
  "generated_at": "2026-03-23T10:02:00Z",
  "shared_threshold": 2,
  "feature_cone_count": 4,
  "infrastructure_node_count": 2,
  "feature_cones": [
    {
      "cone_id": "feature_request_handling",
      "name": "请求处理",
      "entry_point": "/Users/user/projects/flask/src/flask/views.py",
      "entry_point_relative": "src/flask/views.py",
      "exclusive_files": [
        "/Users/user/projects/flask/src/flask/views.py",
        "/Users/user/projects/flask/src/flask/wrappers.py"
      ],
      "exclusive_file_count": 2,
      "exclusive_total_tokens": 5880,
      "layers_within_cone": {
        "0": ["/Users/user/projects/flask/src/flask/wrappers.py"],
        "1": ["/Users/user/projects/flask/src/flask/views.py"]
      },
      "shared_deps": [
        "/Users/user/projects/flask/src/flask::scc_0",
        "/Users/user/projects/flask/src/flask/sansio/app.py"
      ],
      "dag_layer": 3,
      "cohesion_score": 0.78,
      "review_flagged": false
    },
    {
      "cone_id": "feature_cli",
      "name": "CLI 命令行接口",
      "entry_point": "/Users/user/projects/flask/src/flask/cli.py",
      "entry_point_relative": "src/flask/cli.py",
      "exclusive_files": [
        "/Users/user/projects/flask/src/flask/cli.py"
      ],
      "exclusive_file_count": 1,
      "exclusive_total_tokens": 8750,
      "layers_within_cone": {
        "0": ["/Users/user/projects/flask/src/flask/cli.py"]
      },
      "shared_deps": [
        "/Users/user/projects/flask/src/flask::scc_0"
      ],
      "dag_layer": 3,
      "cohesion_score": 1.0,
      "review_flagged": false
    }
  ],
  "infrastructure": [
    {
      "node_id": "/Users/user/projects/flask/src/flask::scc_0",
      "name": "核心应用运行时",
      "members": [
        "/Users/user/projects/flask/src/flask/app.py",
        "/Users/user/projects/flask/src/flask/ctx.py",
        "/Users/user/projects/flask/src/flask/globals.py"
      ],
      "is_scc": true,
      "shared_by_cone_count": 4,
      "shared_by_cones": ["feature_request_handling", "feature_cli", "feature_testing", "feature_blueprints"],
      "dag_layer": 2,
      "total_tokens": 24650
    },
    {
      "node_id": "/Users/user/projects/flask/src/flask/sansio/app.py",
      "name": "SansIO 应用抽象层",
      "members": ["/Users/user/projects/flask/src/flask/sansio/app.py"],
      "is_scc": false,
      "shared_by_cone_count": 4,
      "shared_by_cones": ["feature_request_handling", "feature_cli", "feature_testing", "feature_blueprints"],
      "dag_layer": 1,
      "total_tokens": 8914
    }
  ],
  "review_flags": []
}
```

**`cohesion_score` 计算**：`内部边数 / (内部边数 + 外部边数)`。低于 0.3 时 `review_flagged: true`，该 cone 需要 Validator Agent 审查。

### 4.4 `04_file_tokens.json`：每文件 Token 估算

```json
{
  "schema_version": "2.0",
  "project_root": "/Users/user/projects/flask",
  "generated_at": "2026-03-23T10:03:00Z",
  "estimation_method": "char_count_divided_by_language_factor",
  "language_factors": {
    "python": 3.5,
    "typescript": 4.0,
    "javascript": 3.8
  },
  "fallback_method": "line_count_times_factor",
  "fallback_factors": {
    "python": 12,
    "typescript": 15,
    "javascript": 15
  },
  "total_project_tokens": 142580,
  "files": [
    {
      "path": "/Users/user/projects/flask/src/flask/app.py",
      "relative_path": "src/flask/app.py",
      "language": "python",
      "line_count": 1234,
      "char_count": 45678,
      "estimated_tokens": 13051,
      "estimation_method": "char_count",
      "char_count_available": true
    },
    {
      "path": "/Users/user/projects/flask/src/flask/sansio/scaffold.py",
      "relative_path": "src/flask/sansio/scaffold.py",
      "language": "python",
      "line_count": 512,
      "char_count": 17920,
      "estimated_tokens": 5120,
      "estimation_method": "char_count",
      "char_count_available": true
    }
  ],
  "summary_by_cone": {
    "feature_request_handling": {
      "exclusive_tokens": 5880,
      "shared_infra_tokens": 33564,
      "total_cone_tokens": 39444
    },
    "feature_cli": {
      "exclusive_tokens": 8750,
      "shared_infra_tokens": 33564,
      "total_cone_tokens": 42314
    }
  }
}
```

**Token 估算优先级**：
1. 如果 `char_count` 可用（graph-sitter 提供了 `sf.source`）→ 使用 `char_count / language_factor`
2. 如果只有 `line_count` → 使用 `line_count * line_factor`（误差较大，±50%）
3. `char_count` 在当前实现中通过 `content = sf.source` 后计数字符获得

**注意**：当前 `codebase.py` 中 `FileInfo` 未存储 `char_count`。V2 需要在 `_extract_file` 中将 `len(content)` 存入 `FileInfo`，或在 `04_file_tokens.json` 生成阶段通过 `get_file_content()` 重新读取文件。

### 4.5 `05_task_manifest.json`：Agent 任务分配

```json
{
  "schema_version": "2.0",
  "project_root": "/Users/user/projects/flask",
  "generated_at": "2026-03-23T10:04:00Z",
  "context_budget": 100000,
  "bin_packing_algorithm": "first_fit_decreasing",
  "total_tasks": 5,
  "tasks": [
    {
      "task_id": "task_001",
      "type": "single",
      "description": "分析 CLI 功能锥体（单锥体，独立分析）",
      "feature_cones": ["feature_cli"],
      "files": [
        "/Users/user/projects/flask/src/flask/cli.py"
      ],
      "infrastructure_context": [
        "/Users/user/projects/flask/src/flask::scc_0"
      ],
      "exclusive_tokens": 8750,
      "infra_context_tokens": 2000,
      "total_tokens": 10750,
      "context_budget": 100000,
      "remaining_budget": 89250,
      "dag_layer_range": [3, 3],
      "dependencies": [],
      "output_files": [
        ".codebase-docs/feature_cli/DETAIL.md"
      ]
    },
    {
      "task_id": "task_002",
      "type": "batch",
      "description": "合并分析请求处理和测试工具（共享依赖相同，合并节省上下文）",
      "feature_cones": ["feature_request_handling", "feature_testing"],
      "files": [
        "/Users/user/projects/flask/src/flask/views.py",
        "/Users/user/projects/flask/src/flask/wrappers.py",
        "/Users/user/projects/flask/src/flask/testing.py"
      ],
      "infrastructure_context": [
        "/Users/user/projects/flask/src/flask::scc_0"
      ],
      "exclusive_tokens": 14280,
      "infra_context_tokens": 2000,
      "total_tokens": 16280,
      "context_budget": 100000,
      "remaining_budget": 83720,
      "dag_layer_range": [3, 3],
      "dependencies": [],
      "output_files": [
        ".codebase-docs/feature_request_handling/DETAIL.md",
        ".codebase-docs/feature_testing/DETAIL.md"
      ]
    },
    {
      "task_id": "task_003",
      "type": "split",
      "description": "核心基础设施拆分分析（tokens 超出单次预算，按 DAG 层分批）",
      "feature_cones": ["infrastructure_core"],
      "split_total_parts": 2,
      "split_part_index": 1,
      "files": [
        "/Users/user/projects/flask/src/flask/app.py"
      ],
      "infrastructure_context": [],
      "exclusive_tokens": 13051,
      "infra_context_tokens": 0,
      "total_tokens": 13051,
      "context_budget": 100000,
      "remaining_budget": 86949,
      "dag_layer_range": [2, 2],
      "dependencies": ["task_004"],
      "output_files": [
        ".codebase-docs/infrastructure_core/app_DETAIL.md"
      ]
    },
    {
      "task_id": "task_004",
      "type": "split",
      "description": "核心基础设施拆分分析（第2部分）",
      "feature_cones": ["infrastructure_core"],
      "split_total_parts": 2,
      "split_part_index": 2,
      "files": [
        "/Users/user/projects/flask/src/flask/ctx.py",
        "/Users/user/projects/flask/src/flask/globals.py"
      ],
      "infrastructure_context": [],
      "exclusive_tokens": 11600,
      "infra_context_tokens": 0,
      "total_tokens": 11600,
      "context_budget": 100000,
      "remaining_budget": 88400,
      "dag_layer_range": [2, 2],
      "dependencies": [],
      "output_files": [
        ".codebase-docs/infrastructure_core/ctx_globals_DETAIL.md"
      ]
    },
    {
      "task_id": "task_005",
      "type": "single",
      "description": "INDEX Agent 综合分析（不读源码，汇总所有 DETAIL 产出 INDEX）",
      "feature_cones": ["all"],
      "files": [],
      "infrastructure_context": [],
      "exclusive_tokens": 0,
      "infra_context_tokens": 8000,
      "total_tokens": 8000,
      "context_budget": 100000,
      "remaining_budget": 92000,
      "dag_layer_range": null,
      "dependencies": ["task_001", "task_002", "task_003", "task_004"],
      "output_files": [
        ".codebase-docs/INDEX.md",
        ".codebase-docs/doc-index.json"
      ]
    }
  ]
}
```

---

## 5. 装箱算法伪代码

```python
CONTEXT_BUDGET = 100_000       # tokens，单个 Agent 上下文最大值
SPLIT_FILL_RATIO = 0.8         # 拆分时每部分填充到预算的 80%
INFRA_CONTEXT_TOKENS = 2_000   # 基础设施摘要上下文预算（每任务固定分配）

def bin_pack_tasks(feature_cones: list[FeatureCone],
                   infra_nodes: list[InfraNode]) -> list[Task]:
    """
    First-Fit Decreasing 装箱算法，将功能锥体分配到 Agent 任务中。

    任务类型：
      "split"  - 单个锥体超过上下文预算，必须拆分
      "single" - 单个锥体独自占满一个任务
      "batch"  - 多个小锥体合并到一个任务中
    """
    tasks: list[Task] = []
    task_id_counter = 1

    # Step 1: 按 exclusive_tokens 降序排序（最大锥体优先处理）
    sorted_cones = sorted(feature_cones,
                          key=lambda c: c.exclusive_tokens,
                          reverse=True)

    # Step 2: 处理基础设施节点（先处理，因为其他任务都依赖它们）
    infra_tasks = _handle_infrastructure(infra_nodes, task_id_counter)
    tasks.extend(infra_tasks)
    task_id_counter += len(infra_tasks)
    infra_task_ids = [t.task_id for t in infra_tasks]

    # Step 3: 处理每个功能锥体
    open_batches: list[BatchBin] = []  # 当前开放的批次（还有空间）

    for cone in sorted_cones:
        usable_budget = CONTEXT_BUDGET - INFRA_CONTEXT_TOKENS

        if cone.exclusive_tokens > usable_budget:
            # Case A: 超出预算 → 拆分（split）
            n_parts = math.ceil(cone.exclusive_tokens / (usable_budget * SPLIT_FILL_RATIO))
            split_tasks = _split_cone_by_dag_layer(cone, n_parts, task_id_counter)
            # 拆分任务有依赖关系（后续 split 依赖前一个 split 的摘要）
            for i, st in enumerate(split_tasks):
                if i > 0:
                    st.dependencies.extend([split_tasks[i-1].task_id])
                st.dependencies.extend(infra_task_ids)
            tasks.extend(split_tasks)
            task_id_counter += len(split_tasks)

        else:
            # Case B: 尝试装入现有批次（First Fit）
            placed = False
            for batch in open_batches:
                if batch.remaining_tokens >= cone.exclusive_tokens:
                    batch.add(cone)
                    placed = True
                    break

            if not placed:
                # 开新批次
                new_batch = BatchBin(capacity=usable_budget, task_id=f"task_{task_id_counter:03d}")
                new_batch.add(cone)
                open_batches.append(new_batch)
                task_id_counter += 1

    # Step 4: 将所有批次转换为 Task 对象
    for batch in open_batches:
        task_type = "batch" if len(batch.cones) > 1 else "single"
        t = Task(
            task_id=batch.task_id,
            type=task_type,
            feature_cones=[c.cone_id for c in batch.cones],
            files=[f for c in batch.cones for f in c.exclusive_files],
            infrastructure_context=[n.node_id for n in infra_nodes],
            exclusive_tokens=batch.used_tokens,
            infra_context_tokens=INFRA_CONTEXT_TOKENS,
            total_tokens=batch.used_tokens + INFRA_CONTEXT_TOKENS,
            dependencies=list(infra_task_ids),
        )
        tasks.append(t)

    # Step 5: 最后添加 INDEX Agent 任务（依赖所有 DETAIL 任务）
    detail_task_ids = [t.task_id for t in tasks]
    index_task = Task(
        task_id=f"task_{task_id_counter:03d}",
        type="single",
        feature_cones=["all"],
        files=[],
        infrastructure_context=[],
        exclusive_tokens=0,
        infra_context_tokens=8000,
        total_tokens=8000,
        dependencies=detail_task_ids,
    )
    tasks.append(index_task)

    return tasks


def _split_cone_by_dag_layer(cone: FeatureCone, n_parts: int, start_id: int) -> list[Task]:
    """
    按 DAG 层级拆分大型锥体。

    拆分策略：优先按 DAG 层（同层文件分在一起），而不是任意切割。
    这样每个拆分任务都有完整的层级上下文，不会出现依赖被截断的情况。

    例：infrastructure_core 有 layer=2 和 layer=1 的文件：
      split_part_1: layer=2 文件（app.py，最复杂）
      split_part_2: layer=1 文件（ctx.py, globals.py）
      split_part_3: layer=0 文件（scaffold.py）
    """
    # 按 DAG 层降序分组（高层先分析，因为提供更高抽象视角）
    files_by_layer = group_files_by_dag_layer(cone.exclusive_files, cone.layers_within_cone)
    sorted_layers = sorted(files_by_layer.keys(), reverse=True)

    parts: list[list[str]] = []
    current_part: list[str] = []
    current_tokens = 0
    target_tokens = cone.exclusive_tokens / n_parts

    for layer in sorted_layers:
        for f in files_by_layer[layer]:
            f_tokens = get_file_tokens(f)
            if current_tokens + f_tokens > target_tokens * 1.2 and current_part:
                parts.append(current_part)
                current_part = [f]
                current_tokens = f_tokens
            else:
                current_part.append(f)
                current_tokens += f_tokens

    if current_part:
        parts.append(current_part)

    return [
        Task(
            task_id=f"task_{start_id + i:03d}",
            type="split",
            feature_cones=[cone.cone_id],
            split_total_parts=len(parts),
            split_part_index=i + 1,
            files=part_files,
            dependencies=[f"task_{start_id + i - 1:03d}"] if i > 0 else [],
        )
        for i, part_files in enumerate(parts)
    ]


def _handle_infrastructure(infra_nodes: list[InfraNode], start_id: int) -> list[Task]:
    """
    处理基础设施节点的任务分配。
    基础设施节点按 DAG 层从低到高分析（先分析底层，再分析依赖它的上层）。
    """
    infra_tasks = []
    # 按 DAG 层升序排序（layer=0 最先，因为其他基础设施可能依赖它）
    sorted_infra = sorted(infra_nodes, key=lambda n: n.dag_layer)

    for i, node in enumerate(sorted_infra):
        task_id = f"task_{start_id + i:03d}"
        prev_infra_ids = [f"task_{start_id + j:03d}" for j in range(i)]
        infra_tasks.append(Task(
            task_id=task_id,
            type="single",
            feature_cones=["infrastructure"],
            files=node.members,
            total_tokens=node.total_tokens,
            dependencies=prev_infra_ids,
        ))

    return infra_tasks
```

---

## 6. Louvain 降级触发条件

| 条件 | 具体判断 | 使用策略 | 理由 |
|---|---|---|---|
| 项目有多个一级子目录，且各目录文件数 >= 3 | `len([d for d in subdirs if file_count(d) >= 3]) >= 2` | **目录树优先**：每个子目录 = 一个候选模块 | 开发者的目录组织意图 > 任何算法 |
| 单一根目录，文件数 <= 10 | `depth==1 and len(files) <= 10` | **无分组**：所有文件归为一个模块 | 项目太小，无需分组 |
| 单一根目录，10 < 文件数 <= 20 | `depth==1 and 10 < len(files) <= 20` | **Louvain 全图分组** | 需要找到功能聚类，但规模仍可处理 |
| 单一大目录，文件数 > 20 | `depth==1 and len(files) > 20` | **Louvain + 最大社区大小约束**（max=8文件/社区） | 规模过大，强制细分避免超级社区 |
| 子目录内文件数 > 15 | `file_count(subdir) > 15` | **对该子目录单独运行 Louvain 子分组** | 单目录过大，需要内部细分 |
| 跨目录功能关联（SCC 跨越多目录） | `len(set(parent_dir(f) for f in scc.members)) > 1` | **SCC 优先**：跨目录 SCC 整体归为同一模块 | 强连通分量不可拆，目录边界需要打破 |
| Louvain 结果凝聚度 < 0.3 | `cohesion = internal_edges / (internal_edges + external_edges) < 0.3` | **标记为 `review_flagged=true`**，送审查 Agent | 算法发现了分组可能不合理的信号 |
| 所有方案均失败（孤立节点、空图等）| `graph.number_of_edges() == 0` | **全部文件归入一个模块** | 降级兜底，保证流水线不中断 |

**Louvain 参数建议**：
- `resolution=1.0`：标准分辨率，适合大多数情况
- `resolution=1.5`：当一个目录需要被进一步细分时使用（产生更小的社区）
- `random_state=42`：确保结果可重现

---

## 7. 遗留问题与实现时需验证的假设

### 7.1 API 层面的假设（需要验证）

| 假设 | 验证方法 | 若假设为假的回退 |
|---|---|---|
| `func.dependencies` 返回的路径是绝对路径 | `print(snapshot.functions[0].dependencies)` 查看样本 | 若是相对路径，需在解析时 `os.path.join(root_path, dep)` |
| `FunctionInfo.calls` 中的函数名与 `FunctionInfo.name` 完全一致（大小写、前缀等） | 交叉比对 `func.name` 和 `func.calls` 的值 | 若不一致需规范化（strip、lower 等）|
| `ClassInfo.base_classes` 仅包含项目内定义的类，不包含外部库的类 | 检查 `Flask.base_classes` 是否包含 `"Scaffold"` 等外部类 | 若包含外部类，需要通过 `class_name in class_name_to_file` 过滤 |
| graph-sitter `sf.source` 属性总是可用（用于 char_count 计算） | 检查 `getattr(sf, "source", None)` 是否为 None | 若不可用，回退到 `line_count * 4 * CHARS_PER_LINE` |

### 7.2 算法层面的假设（需要验证）

| 假设 | 验证方法 | 若假设为假的回退 |
|---|---|---|
| SCC 压缩后的 DAG 保证无环（DAG 的定义要求） | `nx.is_directed_acyclic_graph(condensed)` 返回 True | 理论上保证，若失败则是 NetworkX bug |
| Flask 项目有至少一个 in-degree=0 的节点 | 运行后检查 `find_feature_roots` 的输出 | 若无，启用库代码 fallback（取最小 in-degree 节点）|
| `nx.condensation()` 的节点 `members` 属性存在 | NetworkX 3.x 文档确认 | 若属性名不同，查看 `condensed.nodes[n]` 的所有属性 |
| Louvain 在小图（< 5节点）上能正常运行 | 测试 5 节点以内的图 | 若失败，对小图直接用目录前缀分组 |

### 7.3 设计决策层面的待确认项

| 决策 | 当前选择 | 待验证 |
|---|---|---|
| 函数名重名时跳过调用边 | 保守策略（不建错误边） | 是否应该改为"所有同名函数都建边"（宽松策略）？ |
| 共享基础设施阈值 | threshold=2（被 2 个以上 cone 使用 → 基础设施）| 对于有大量公共代码的项目（如框架），是否应该提高到 3？ |
| SCC 内文件在 `05_task_manifest.json` 中的处理 | SCC 整体作为一个分析单元 | 若 SCC 内文件总 token 超出预算，如何拆分？（当前算法未处理此 edge case）|
| `char_count` 的获取方式 | 在 `_extract_file` 中通过 `len(sf.source)` 获取 | 需确认修改 `FileInfo` dataclass 是否会破坏现有序列化代码 |
| INFRA_CONTEXT_TOKENS 固定值 2000 | 每个任务预留 2000 tokens 给基础设施摘要 | 对于大型基础设施（>50K tokens），2000 tokens 的摘要是否足够？|

### 7.4 边界情况（Edge Cases）

- **空项目**：文件数为 0 → 直接返回空的 5 个 JSON 文件
- **单文件项目**：1个文件 → 1个 cone，无 DAG，无 SCC，单任务
- **全相互循环的项目**：所有文件形成一个大 SCC → 整个项目是一个 SCC 节点，feature cone 分析退化为"所有文件是一个 cone"
- **大型 SCC 超出 CONTEXT_BUDGET**：例如 Flask 的 SCC {app.py+ctx.py+globals.py} 若总 token > 100K → 需要对 SCC 内文件做装箱分配，但依赖关系分析结果需要明确标注"此为同一 SCC 的不同部分"
- **纯扁平项目 + 零依赖（无 import 关系）**：所有文件互相独立 → 图无边 → 每个文件是自己的 cone → 每个文件是独立任务
