# 动态文档深度策略

> **作者**：架构设计 Agent
> **创建时间**：2026-03-22
> **状态**：设计文档（T-02）
> **依赖项**：architecture.md

---

## 目录

1. [问题陈述](#1-问题陈述)
2. [核心算法：深度决策引擎](#2-核心算法深度决策引擎)
3. [拆分策略选择](#3-拆分策略选择)
4. [Token 预算分配](#4-token-预算分配)
5. [递归终止条件](#5-递归终止条件)
6. [最小可文档化单元](#6-最小可文档化单元)
7. [Flask 项目验证示例](#7-flask-项目验证示例)
8. [配置参考](#8-配置参考)

---

## 1. 问题陈述

固定层文档（始终生成 3 层）存在以下问题：

- **对小型模块过度文档化**：一个 200 行的工具模块不需要 4 层详细说明
- **对大型模块文档不足**：一个有 50+ 个文件的框架子系统需要超过 3 层
- **Token 预算浪费**：固定分配无法适应实际内容复杂度

**解决方案**：动态深度算法，基于模块指标自适应调整每个模块的文档深度（0-5 层）。

---

## 2. 核心算法：深度决策引擎

### 2.1 输入与输出

```python
@dataclass(frozen=True)
class ModuleMetrics:
    """用于深度决策的输入指标。"""
    file_count: int               # 模块中的文件总数
    function_count: int           # 所有文件中的函数总数
    class_count: int              # 所有文件中的类总数
    line_count: int               # 总代码行数（不含注释和空行）
    estimated_tokens: int         # 源码的估算 Token 数
    subpackage_count: int         # 直接子目录数量
    dependency_count: int         # 有向图中的传入依赖数
    cyclomatic_complexity: float  # 所有函数的平均圈复杂度
    is_utility_module: bool       # 是否为高入度工具模块
    has_clear_entry_point: bool   # 是否有唯一的入口点文件

@dataclass(frozen=True)
class DocumentPlan:
    """深度决策的输出。"""
    depth: int                          # 0-5
    split_strategy: SplitStrategy       # 如何拆分子文档
    doc_budget_per_level: tuple[int, ...] # 每层的 Token 预算
    should_merge_parent: bool           # 合并到父文档而非单独生成
    termination_reason: str             # 为何在此深度停止
```

### 2.2 深度计算

主公式：

```
depth = max(structural_depth, complexity_depth, token_depth)
```

应用约束后：

- 工具模块上限为深度 2
- 非常小的模块（< 100 行，< 5 个函数）强制为深度 0
- 全局上限为 5

#### 结构深度（基于子包数量）

| subpackage_count | structural_depth |
| ---------------- | ---------------- |
| 0                | 0                |
| 1                | 1                |
| 2-4              | 2                |
| 5-9              | 3                |
| 10-19            | 4                |
| >= 20            | 5                |

#### 复杂度深度（基于函数/类/行数/圈复杂度）

```python
def complexity_score(metrics: ModuleMetrics) -> float:
    """计算归一化复杂度分数（0.0-1.0）。"""
    # 各组件独立归一化后加权平均
    func_score = min(metrics.function_count / 100, 1.0)      # 权重 0.35
    class_score = min(metrics.class_count / 20, 1.0)         # 权重 0.25
    line_score = min(metrics.line_count / 5000, 1.0)         # 权重 0.25
    cc_score = min(metrics.cyclomatic_complexity / 10, 1.0)  # 权重 0.15
    return (
        0.35 * func_score +
        0.25 * class_score +
        0.25 * line_score +
        0.15 * cc_score
    )

def complexity_depth(score: float) -> int:
    if score < 0.2:  return 0
    if score < 0.4:  return 1
    if score < 0.6:  return 2
    if score < 0.8:  return 3
    return 4
```

#### Token 深度（基于估算源码 Token 数）

| estimated_tokens | token_depth |
| ---------------- | ----------- |
| < 5,000          | 0           |
| 5,000-15,000     | 1           |
| 15,000-40,000    | 2           |
| 40,000-80,000    | 3           |
| 80,000-150,000   | 4           |
| >= 150,000       | 5           |

### 2.3 完整深度计算流程

```python
def calculate_depth(metrics: ModuleMetrics) -> int:
    """计算模块的最优文档深度。"""
    # 1. 强制合并极小模块
    if metrics.line_count < 100 and metrics.function_count < 5:
        return 0

    # 2. 计算三个独立深度分数
    s_depth = structural_depth(metrics.subpackage_count)
    c_depth = complexity_depth(complexity_score(metrics))
    t_depth = token_depth(metrics.estimated_tokens)

    # 3. 取最大值
    raw_depth = max(s_depth, c_depth, t_depth)

    # 4. 应用约束
    if metrics.is_utility_module:
        raw_depth = min(raw_depth, 2)

    return min(raw_depth, 5)
```

---

## 3. 拆分策略选择

当深度 >= 2 时，需要决定如何拆分子文档。

### 3.1 策略定义

| 策略             | 描述             | 每个子文档覆盖的内容 |
| ---------------- | ---------------- | -------------------- |
| `SUBPACKAGE`     | 按目录拆分       | 每个直接子目录       |
| `CLASS`          | 按类拆分         | 每个主要类           |
| `FUNCTION_GROUP` | 按功能域分组函数 | 相关函数的集群       |
| `FILE`           | 按文件拆分       | 每个源文件           |
| `HYBRID`         | 混合方式         | 子包 + 类            |

### 3.2 选择规则

优先级顺序：`SUBPACKAGE > CLASS > FUNCTION_GROUP > FILE`

```python
def select_split_strategy(metrics: ModuleMetrics) -> SplitStrategy:
    """为子文档选择最优拆分策略。"""

    # 规则 1：子包优先（最自然的拆分方式）
    if metrics.subpackage_count >= 2:
        avg_size = metrics.file_count / metrics.subpackage_count
        if avg_size >= 3:  # 每个子包至少 3 个文件
            return SplitStrategy.SUBPACKAGE

    # 规则 2：OOP 风格 → 按类拆分
    if metrics.class_count >= 3 and metrics.class_count <= 20:
        avg_methods = metrics.function_count / max(metrics.class_count, 1)
        if avg_methods >= 3:  # 每个类至少 3 个方法
            return SplitStrategy.CLASS

    # 规则 3：函数式风格 → 按函数组拆分
    if metrics.function_count >= 10 and metrics.class_count <= 2:
        return SplitStrategy.FUNCTION_GROUP

    # 规则 4：混合内容 → 混合策略
    if metrics.subpackage_count >= 1 and metrics.class_count >= 3:
        return SplitStrategy.HYBRID

    # 规则 5：兜底 → 按文件拆分
    return SplitStrategy.FILE
```

---

## 4. Token 预算分配

### 4.1 总预算计算

```python
def calculate_total_budget(
    estimated_source_tokens: int,
    max_depth: int,
) -> int:
    """为整个文档树计算总 Token 预算。

    公式：
        total = source_tokens * 0.15 * (1 + depth * 0.5)

    理由：
    - 0.15 = 文档约为源代码的 15%（高密度摘要）
    - depth 乘数：更深的文档需要更多 Token 来覆盖所有层级
    """
    base_ratio = 0.15
    depth_multiplier = 1 + max_depth * 0.5
    return int(estimated_source_tokens * base_ratio * depth_multiplier)
```

### 4.2 按层级分配（几何衰减）

```python
DECAY_FACTOR = 0.6  # 可通过配置覆盖

def allocate_budget_per_level(
    total_budget: int,
    max_depth: int,
) -> tuple[int, ...]:
    """使用几何衰减在层级间分配预算。

    层级 0 权重：1.0
    层级 1 权重：0.6
    层级 2 权重：0.36
    ...

    实际分配值 = 归一化权重 * total_budget
    每层还要强制执行最小值。
    """
    MIN_BUDGETS = {0: 600, 1: 1000, 2: 1500, 3: 1200, 4: 800}

    weights = [DECAY_FACTOR ** level for level in range(max_depth + 1)]
    total_weight = sum(weights)
    allocations = []
    for level, weight in enumerate(weights):
        raw = int(total_budget * weight / total_weight)
        minimum = MIN_BUDGETS.get(level, 500)
        allocations.append(max(raw, minimum))
    return tuple(allocations)
```

### 4.3 每层预算范围

| 层级          | 最小值 | 最大值 | 推荐值      | 策略         |
| ------------- | ------ | ------ | ----------- | ------------ |
| 0（INDEX）    | 600    | 1,200  | 800-1,000   | 固定         |
| 1（OVERVIEW） | 1,000  | 2,000  | 1,200-1,500 | 按复杂度缩放 |
| 2（DETAIL）   | 1,500  | 3,500  | 2,000-2,500 | 稳定分配     |
| 3（DETAIL）   | 1,200  | 2,500  | 1,500-2,000 | 递减         |
| 4（DETAIL）   | 800    | 2,000  | 1,000-1,500 | 递减         |
| 5+（DETAIL）  | 500    | 1,500  | 800-1,000   | 最低可行值   |

---

## 5. 递归终止条件

文档生成在满足以下任一条件时停止，不再向更深层递归：

| 终止原因                     | 条件                                 | 说明                   |
| ---------------------------- | ------------------------------------ | ---------------------- |
| `max_depth_reached`          | current_depth == configured_max      | 达到全局深度上限       |
| `below_min_lines`            | line_count < 30                      | 内容太少，合并到父文档 |
| `below_min_functions`        | function_count < 2                   | 函数太少，合并到父文档 |
| `budget_exhausted`           | remaining_budget < 200               | 预算耗尽               |
| `no_meaningful_split`        | 不能创建 2+ 个可文档化子单元         | 无法进一步拆分         |
| `utility_module_depth_limit` | is_utility and depth == 2            | 工具模块深度上限       |
| `single_unit_file`           | file_count == 1 and class_count <= 1 | 单文件单类             |

---

## 6. 最小可文档化单元

低于以下阈值的单元被合并到父文档，而非单独生成文件：

| 指标               | 最小值 | 低于时的操作         |
| ------------------ | ------ | -------------------- |
| 代码行数           | 30     | 作为父文档的内联部分 |
| 函数数             | 2      | 合并到父文档         |
| 类数（针对类拆分） | 1      | 合并到父文档         |
| 估算 Token 数      | 200    | 作为父文档的摘要行   |

**合并规则**：

```python
def should_merge_into_parent(metrics: ModuleMetrics) -> bool:
    """确定该模块是否太小，应合并到父文档。"""
    if metrics.line_count < 30:
        return True
    if metrics.function_count < 2 and metrics.class_count == 0:
        return True
    if metrics.estimated_tokens < 200:
        return True
    return False
```

---

## 7. Flask 项目验证示例

以 Flask 框架（约 2.4 万行 Python 代码）为例验证算法：

### 7.1 模块分析结果

| 模块       | 行数  | 文件数 | 函数数 | 类数 | 子包数 |
| ---------- | ----- | ------ | ------ | ---- | ------ |
| core       | 2,400 | 8      | 45     | 12   | 0      |
| routing    | 1,800 | 6      | 38     | 8    | 0      |
| templating | 1,200 | 4      | 22     | 5    | 0      |
| cli        | 600   | 3      | 18     | 2    | 0      |
| testing    | 800   | 4      | 25     | 3    | 0      |
| utils      | 400   | 3      | 15     | 1    | 0      |

### 7.2 算法应用结果

| 模块       | structural | complexity | token | 最终深度              | 拆分策略       |
| ---------- | ---------- | ---------- | ----- | --------------------- | -------------- |
| core       | 0          | 3          | 2     | **3**                 | CLASS          |
| routing    | 0          | 3          | 2     | **3**                 | CLASS          |
| templating | 0          | 2          | 1     | **2**                 | CLASS          |
| cli        | 0          | 1          | 1     | **1**                 | --             |
| testing    | 0          | 2          | 1     | **2**                 | FUNCTION_GROUP |
| utils      | 0          | 1          | 0     | **1**（工具模块上限） | --             |

### 7.3 预算分配示例（core 模块）

```
总预算：28,800 tokens × 0.15 × (1 + 3 × 0.5) = 6,480 tokens

按层分配（衰减系数 0.6）：
  权重：[1.0, 0.6, 0.36, 0.216]，总权重 = 2.176

  层级 0 (INDEX)：   6,480 × 1.0/2.176 ≈ 2,978 → 限制为 1,200（上限）
  层级 1 (OVERVIEW)：6,480 × 0.6/2.176 ≈ 1,787 → 保留为 1,787
  层级 2 (DETAIL)：  6,480 × 0.36/2.176 ≈ 1,072 → 限制为 1,500（下限）
  层级 3 (DETAIL)：  6,480 × 0.216/2.176 ≈ 643 → 限制为 1,200（下限）
```

---

## 8. 配置参考

### 8.1 doc-config.yaml 模式

```yaml
# 全局设置
max_depth: 5 # 任意模块的最大深度（0-5）

# 预算设置
budget:
  total_tokens: 50000 # 总 Token 预算上限
  decay_factor: 0.6 # 每层的几何衰减系数

# 深度阈值
depth:
  min_lines_for_split: 200 # 更深文档所需的最小代码行数
  min_components_for_split: 15 # 更深文档所需的最小组件数（函数+类）
  min_files_for_split: 5 # 更深文档所需的最小文件数

# 每层 Token 限制
token_limits:
  index:
    min: 600
    max: 1200
    default: 1000
  overview:
    min: 1000
    max: 2000
    default: 1500
  detail_l2:
    min: 1500
    max: 3500
    default: 2500
  detail_l3:
    min: 1200
    max: 2500
    default: 2000
  detail_l4:
    min: 800
    max: 2000
    default: 1500
  detail_l5plus:
    min: 500
    max: 1500
    default: 1000

# 最小可文档化单元阈值
minimum_unit:
  lines: 30
  functions: 2
  estimated_tokens: 200
```

### 8.2 环境变量覆盖

| 环境变量             | 默认值  | 描述                      |
| -------------------- | ------- | ------------------------- |
| `CE_MAX_DEPTH`       | `5`     | 全局最大深度上限          |
| `CE_DECAY_FACTOR`    | `0.6`   | 预算衰减系数              |
| `CE_MIN_LINES_SPLIT` | `200`   | 触发深层文档的最小行数    |
| `CE_MIN_TOKENS_UNIT` | `200`   | 最小可文档化单元 Token 数 |
| `CE_TOTAL_BUDGET`    | `50000` | 总 Token 预算             |

### 8.3 决策流程图

```
开始
  │
  ▼
行数 < 100 且 函数数 < 5?
  │ 是                │ 否
  ▼                   ▼
返回 深度=0          计算三个深度分数
（合并到父文档）      structural / complexity / token
                      │
                      ▼
                    depth = max(三个分数)
                      │
                      ▼
                    是工具模块？
                      │ 是             │ 否
                      ▼               ▼
                    depth = min(depth, 2)  depth = min(depth, 5)
                      │
                      ▼
                    选择拆分策略
                    SUBPACKAGE > CLASS > FUNCTION_GROUP > FILE
                      │
                      ▼
                    分配每层 Token 预算
                      │
                      ▼
                    返回 DocumentPlan
```

### 8.4 复杂度速查表

| 代码规模             | 预期深度  | 预期拆分策略        | 预期预算范围 |
| -------------------- | --------- | ------------------- | ------------ |
| < 100 行             | 0（合并） | --                  | --           |
| 100-500 行           | 1         | --                  | 1,000-1,500  |
| 500-2,000 行         | 1-2       | CLASS 或 FILE       | 1,500-4,000  |
| 2,000-5,000 行       | 2-3       | CLASS 或 SUBPACKAGE | 4,000-8,000  |
| 5,000-15,000 行      | 3-4       | SUBPACKAGE          | 8,000-15,000 |
| 15,000+ 行           | 4-5       | SUBPACKAGE          | 15,000+      |
| 工具模块（任意大小） | 最大 2    | CLASS 或 FILE       | 最高 4,000   |
