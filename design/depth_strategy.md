# Dynamic Document Depth Strategy

> **Author**: architect agent
> **Created**: 2026-03-22
> **Status**: Design Document
> **Dependencies**: 02_auto_module_grouping.md, 04_progressive_doc_standards.md, 07_context_budget_strategies.md

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Core Algorithm: Depth Decision Engine](#2-core-algorithm-depth-decision-engine)
3. [Split Strategy Selection Rules](#3-split-strategy-selection-rules)
4. [Token Budget Allocation](#4-token-budget-allocation)
5. [Recursive Termination Conditions](#5-recursive-termination-conditions)
6. [Flask Project Validation](#6-flask-project-validation)
7. [Implementation Pseudocode](#7-implementation-pseudocode)
8. [Configuration Reference](#8-configuration-reference)

---

## 1. Problem Statement

### 1.1 The Fixed-Layer Problem

The original v2 design used a fixed 3-layer documentation model:

```
INDEX.md (Level 0) -> OVERVIEW.md (Level 1) -> ARCHITECTURE.md (Level 2)
```

**Problem**: This works poorly for heterogeneous codebases:

| Module Type | Typical Size | Fixed 3-Layer Result | Problem |
|-------------|--------------|---------------------|---------|
| Tiny utility | 50 LOC, 2 files | 3 docs generated | Over-documented; waste of tokens |
| Medium service | 500 LOC, 10 files | 3 docs generated | Good fit |
| Large subsystem | 3000 LOC, 50 files | 3 docs generated | Under-documented; single ARCHITECTURE.md cannot cover complexity |
| Massive framework | 7700 LOC, 24 files | 3 docs generated | Critically under-documented |

### 1.2 Design Goal

Create a **Dynamic Document Depth Planner** that:

1. **Adapts depth to complexity**: Simple modules get fewer docs; complex modules get deeper nesting
2. **Allocates token budget efficiently**: Total documentation budget scales with module importance
3. **Chooses appropriate split strategies**: Subpackage vs class vs function-group based on code structure
4. **Terminates appropriately**: Stop generating when additional docs add no value

---

## 2. Core Algorithm: Depth Decision Engine

### 2.1 Input/Output Specification

```python
# INPUT: Module metrics collected from static analysis
@dataclass
class ModuleMetrics:
    file_count: int           # Number of source files in module
    function_count: int       # Total functions/methods
    class_count: int          # Total classes
    line_count: int           # Total lines of code (non-blank, non-comment)
    estimated_tokens: int     # Token count estimate (chars / 4 for Python)
    subpackage_count: int     # Number of subdirectories that could be submodules
    dependency_count: int     # Number of external dependencies (edges in dep graph)
    cyclomatic_complexity: float  # Average McCabe complexity
    is_utility_module: bool   # Flag for utility/shared modules
    has_clear_entry_point: bool   # Single main file/class exists

# OUTPUT: Documentation plan for this module
@dataclass
class DocumentPlan:
    depth: int                # 0-5 levels of documentation
    split_strategy: SplitStrategy  # How to subdivide
    doc_budget_per_level: list[int]  # Token budget for each level
    should_merge_parent: bool # True if too small, merge into parent
    termination_reason: str   # Why we stopped at this depth
```

### 2.2 Depth Decision Algorithm

**Core principle**: Depth is determined by the *maximum* of three factors:

```
depth = max(structural_depth, complexity_depth, token_depth)
```

#### 2.2.1 Structural Depth (based on subpackage_count)

Structural depth measures the *hierarchical complexity* of the module.

```
IF subpackage_count == 0:
    structural_depth = 0  # Flat module, no nesting needed
ELIF subpackage_count <= 2:
    structural_depth = 1  # Small hierarchy, 1 level of sub-documents
ELIF subpackage_count <= 5:
    structural_depth = 2  # Medium hierarchy
ELIF subpackage_count <= 10:
    structural_depth = 3  # Large hierarchy
ELIF subpackage_count <= 20:
    structural_depth = 4  # Very large hierarchy
ELSE:
    structural_depth = 5  # Massive hierarchy (e.g., Django apps)
```

**Rationale**: Each subpackage represents a logical boundary that may deserve its own documentation subtree.

#### 2.2.2 Complexity Depth (based on function_count, class_count, cyclomatic_complexity)

Complexity depth measures the *cognitive load* of understanding the module.

```
complexity_score = (
    function_count * 1.0 +
    class_count * 3.0 +
    line_count / 100.0 +
    cyclomatic_complexity * 2.0
)

IF complexity_score < 10:
    complexity_depth = 0  # Trivial module
ELIF complexity_score < 30:
    complexity_depth = 1  # Simple module
ELIF complexity_score < 100:
    complexity_depth = 2  # Moderate module
ELIF complexity_score < 300:
    complexity_depth = 3  # Complex module
ELIF complexity_score < 600:
    complexity_depth = 4  # Very complex module
ELSE:
    complexity_depth = 5  # Extremely complex module
```

**Threshold derivation**:
- `complexity_score < 10`: e.g., 5 functions + 1 class + 100 LOC + avg CC 2 = 5 + 3 + 1 + 4 = 13 -> actually goes to depth 1
- Recalibrate: 3 functions + 0 classes + 50 LOC + avg CC 1 = 3 + 0 + 0.5 + 2 = 5.5 -> depth 0

#### 2.2.3 Token Depth (based on estimated_tokens)

Token depth measures the *documentation budget needed* to adequately cover the module.

```
IF estimated_tokens < 500:
    token_depth = 0  # Tiny module, single summary suffices
ELIF estimated_tokens < 2000:
    token_depth = 1  # Small module
ELIF estimated_tokens < 8000:
    token_depth = 2  # Medium module
ELIF estimated_tokens < 32000:
    token_depth = 3  # Large module
ELIF estimated_tokens < 128000:
    token_depth = 4  # Very large module
ELSE:
    token_depth = 5  # Massive module
```

**Rationale**: Each level of documentation should fit within a target token budget (see Section 4). When source code exceeds thresholds, more levels are needed to break it down.

#### 2.2.4 Final Depth Calculation

```python
def calculate_depth(metrics: ModuleMetrics) -> int:
    """
    Calculate the optimal documentation depth for a module.

    Returns: 0-5
    """
    # Calculate individual depth factors
    structural_depth = _calc_structural_depth(metrics.subpackage_count)
    complexity_depth = _calc_complexity_depth(
        metrics.function_count,
        metrics.class_count,
        metrics.line_count,
        metrics.cyclomatic_complexity
    )
    token_depth = _calc_token_depth(metrics.estimated_tokens)

    # Take maximum - the most demanding factor determines depth
    raw_depth = max(structural_depth, complexity_depth, token_depth)

    # Apply constraints
    if metrics.is_utility_module:
        # Utility modules never exceed depth 2 (they're infrastructure)
        raw_depth = min(raw_depth, 2)

    if metrics.line_count < 100 and metrics.function_count < 5:
        # Very small modules are merged into parent
        raw_depth = 0

    # Cap at 5 (maximum supported depth)
    return min(raw_depth, 5)
```

### 2.3 Depth Semantics

| Depth | Meaning | Document Types Generated |
|-------|---------|-------------------------|
| 0 | Summary only | Single paragraph in parent's OVERVIEW.md |
| 1 | Flat overview | OVERVIEW.md only (no sub-documents) |
| 2 | Two-level | OVERVIEW.md + one level of ARCHITECTURE.md |
| 3 | Three-level | OVERVIEW.md + subpackage OVERVIEW.md + ARCHITECTURE.md |
| 4 | Four-level | Full 4-level nesting (rare, for large subsystems) |
| 5 | Five-level | Maximum depth (reserved for framework-scale modules) |

---

## 3. Split Strategy Selection Rules

When depth > 1, the module must be *split* into sub-documents. The choice of split strategy determines how this is done.

### 3.1 Strategy Options

```python
class SplitStrategy(Enum):
    SUBPACKAGE = "subpackage"      # Split by subdirectory/module
    CLASS = "class"                # Split by class (OOP-heavy code)
    FUNCTION_GROUP = "function_group"  # Split by related functions
    FILE = "file"                  # Split by individual files (last resort)
    HYBRID = "hybrid"              # Combination of above
```

### 3.2 Decision Tree for Split Strategy

```python
def select_split_strategy(metrics: ModuleMetrics) -> SplitStrategy:
    """
    Select the optimal split strategy based on module characteristics.

    Priority: SUBPACKAGE > CLASS > FUNCTION_GROUP > FILE
    """

    # RULE 1: If subpackages exist and are meaningful, prefer subpackage split
    if metrics.subpackage_count >= 2:
        # Check if subpackages are well-balanced (not one dominant + many tiny)
        subpackage_sizes = _get_subpackage_sizes(metrics)
        max_size = max(subpackage_sizes)
        total_size = sum(subpackage_sizes)

        # If largest subpackage is < 60% of total, subpackages are meaningful
        if max_size < 0.6 * total_size:
            return SplitStrategy.SUBPACKAGE

    # RULE 2: If OOP-heavy (many classes, few standalone functions), use class split
    if metrics.class_count >= 3:
        class_to_function_ratio = metrics.class_count / max(metrics.function_count, 1)
        if class_to_function_ratio >= 0.3:  # >= 30% of functions are methods
            return SplitStrategy.CLASS

    # RULE 3: If functional style (few classes, many functions), use function group
    if metrics.function_count >= 5 and metrics.class_count <= 2:
        return SplitStrategy.FUNCTION_GROUP

    # RULE 4: If many files with mixed content, use hybrid
    if metrics.file_count >= 5 and metrics.class_count >= 2 and metrics.function_count >= 10:
        return SplitStrategy.HYBRID

    # RULE 5: Fallback to file-level split
    return SplitStrategy.FILE
```

### 3.3 Strategy Application Details

#### 3.3.1 SUBPACKAGE Strategy

**When to use**:
- `subpackage_count >= 2`
- Subpackages are reasonably balanced
- Directory structure reflects logical boundaries

**How it works**:
```
auth/                           <- OVERVIEW.md (Level 1)
├── login/                      <- OVERVIEW.md (Level 2)
│   ├── handlers.py             <- ARCHITECTURE.md (Level 3)
│   └── validators.py           <- (merged into handlers.md or separate)
├── oauth/                      <- OVERVIEW.md (Level 2)
│   └── oauth_client.py         <- ARCHITECTURE.md (Level 3)
└── middleware/                 <- OVERVIEW.md (Level 2)
    └── auth_middleware.py      <- ARCHITECTURE.md (Level 3)
```

**Token budget split**: Each subpackage gets proportional budget based on its size.

#### 3.3.2 CLASS Strategy

**When to use**:
- OOP-heavy code (`class_count >= 3`, high class-to-function ratio)
- Each class is substantial (> 100 LOC average)
- Classes have clear responsibilities

**How it works**:
```
models/                         <- OVERVIEW.md (Level 1)
├── User (class in models.py)   <- ARCHITECTURE.md (Level 2)
├── Post (class in models.py)   <- ARCHITECTURE.md (Level 2)
└── Comment (class in models.py) <- ARCHITECTURE.md (Level 2)
```

**Token budget split**: Each class gets budget proportional to its method count + complexity.

#### 3.3.3 FUNCTION_GROUP Strategy

**When to use**:
- Functional style code
- Many standalone functions with logical groupings
- Utility modules with cohesive function clusters

**How it works**:
```
utils/                          <- OVERVIEW.md (Level 1)
├── string_utils (group)        <- ARCHITECTURE.md (Level 2)
│   ├── sanitize()
│   ├── truncate()
│   └── format()
├── date_utils (group)          <- ARCHITECTURE.md (Level 2)
│   ├── parse_iso()
│   ├── format_relative()
│   └── is_weekend()
└── file_utils (group)          <- ARCHITECTURE.md (Level 2)
    ├── read_json()
    └── write_json()
```

**Grouping heuristic**:
1. Parse function names and docstrings
2. Cluster by shared prefix (e.g., `str_*`, `date_*`)
3. Cluster by shared dependencies (functions that call each other)
4. Target 3-8 functions per group

#### 3.3.4 HYBRID Strategy

**When to use**:
- Mixed code style
- Some subpackages exist but not comprehensive
- Complex modules with multiple organizational axes

**How it works**:
- First level: SUBPACKAGE split (if available)
- Second level: CLASS or FUNCTION_GROUP depending on content
- Adaptive based on local structure

### 3.4 Minimum Documentable Unit

A sub-document is only created if it meets **minimum thresholds**:

```python
MINIMUM_DOCUMENTABLE_UNIT = {
    "min_lines": 30,           # Fewer lines -> merge into parent
    "min_functions": 2,        # Fewer functions -> merge into parent
    "min_classes": 1,          # At least 1 class for class-split
    "min_tokens": 200,         # Fewer tokens -> not worth separate doc
}

def should_create_subdocument(unit_metrics: ModuleMetrics) -> bool:
    """
    Determine if a unit is large enough to deserve its own document.
    """
    if unit_metrics.line_count < MINIMUM_DOCUMENTABLE_UNIT["min_lines"]:
        return False
    if unit_metrics.estimated_tokens < MINIMUM_DOCUMENTABLE_UNIT["min_tokens"]:
        return False
    if (unit_metrics.function_count < MINIMUM_DOCUMENTABLE_UNIT["min_functions"] and
        unit_metrics.class_count < MINIMUM_DOCUMENTABLE_UNIT["min_classes"]):
        return False
    return True
```

---

## 4. Token Budget Allocation

### 4.1 Total Budget Calculation

The total documentation token budget for a module is calculated as:

```python
def calculate_total_budget(metrics: ModuleMetrics, depth: int) -> int:
    """
    Calculate total documentation token budget.

    Base budget scales with source code size, multiplied by depth factor.
    """
    # Base budget: documentation should be ~10-20% of source token count
    base_ratio = 0.15  # 15% of source tokens for documentation

    # Depth multiplier: each additional level adds ~50% budget
    depth_multiplier = 1.0 + (depth * 0.5)

    # Utility modules get reduced budget (they're simpler to document)
    if metrics.is_utility_module:
        base_ratio *= 0.6

    # Calculate base budget
    base_budget = int(metrics.estimated_tokens * base_ratio * depth_multiplier)

    # Apply bounds
    MIN_BUDGET = 500   # Minimum viable documentation
    MAX_BUDGET = 50000 # Maximum for any single module

    return max(MIN_BUDGET, min(MAX_BUDGET, base_budget))
```

### 4.2 Per-Level Budget Allocation

Budget is distributed across documentation levels using a **geometric decay** model:

```python
def allocate_budget_per_level(total_budget: int, depth: int) -> list[int]:
    """
    Allocate documentation budget across levels.

    Top levels get more budget (broader coverage).
    Deeper levels get less (more focused).

    Pattern: Level 0 gets most, then decay by factor of 0.6 per level.
    """
    if depth == 0:
        return [min(total_budget, 300)]  # Just a summary paragraph

    # Decay factor: each level gets 60% of previous
    decay_factor = 0.6

    # Calculate weights for each level
    weights = [decay_factor ** i for i in range(depth + 1)]
    total_weight = sum(weights)

    # Normalize and allocate
    budgets = [int(total_budget * w / total_weight) for w in weights]

    # Apply minimums per level
    MIN_BUDGETS = {
        0: 800,   # Level 0 (INDEX): at least 800 tokens
        1: 1200,  # Level 1 (OVERVIEW): at least 1200 tokens
        2: 2000,  # Level 2 (ARCHITECTURE): at least 2000 tokens
        3: 1500,  # Level 3+: at least 1500 tokens
        4: 1500,
        5: 1500,
    }

    for i in range(len(budgets)):
        min_budget = MIN_BUDGETS.get(i, 1500)
        budgets[i] = max(budgets[i], min_budget)

    # Re-normalize if we exceeded budget
    total_allocated = sum(budgets)
    if total_allocated > total_budget:
        # Scale down proportionally
        scale = total_budget / total_allocated
        budgets = [int(b * scale) for b in budgets]

    return budgets
```

### 4.3 Budget Allocation Example

For a module with:
- `estimated_tokens`: 10,000
- `depth`: 3
- `is_utility_module`: False

```
total_budget = 10,000 * 0.15 * (1 + 3*0.5) = 10,000 * 0.15 * 2.5 = 3,750 tokens

weights = [1.0, 0.6, 0.36, 0.216] = [1.0, 0.6, 0.36, 0.216]
total_weight = 2.176

Level 0: 3,750 * 1.0 / 2.176 = 1,723 tokens
Level 1: 3,750 * 0.6 / 2.176 = 1,034 tokens
Level 2: 3,750 * 0.36 / 2.176 = 620 tokens
Level 3: 3,750 * 0.216 / 2.176 = 372 tokens

After minimums applied:
Level 0: max(1,723, 800) = 1,723 tokens
Level 1: max(1,034, 1,200) = 1,200 tokens
Level 2: max(620, 2,000) = 2,000 tokens
Level 3: max(372, 1,500) = 1,500 tokens

Total: 6,423 tokens (exceeds budget!)

Re-normalized:
Level 0: 1,723 * (3,750/6,423) = 1,006 tokens
Level 1: 1,200 * (3,750/6,423) = 701 tokens
Level 2: 2,000 * (3,750/6,423) = 1,168 tokens
Level 3: 1,500 * (3,750/6,423) = 876 tokens
```

### 4.4 Content Prioritization When Budget Exceeded

When a level's content exceeds its budget, prioritize as follows:

```python
CONTENT_PRIORITY = [
    # Priority 1 (highest): Always include
    ("module_name", 1.0),
    ("one_line_description", 1.0),
    ("public_interface_signatures", 1.0),

    # Priority 2: Important context
    ("dependency_list", 0.9),
    ("architecture_diagram", 0.85),  # Mermaid, compact
    ("entry_points", 0.8),

    # Priority 3: Detailed content
    ("class_responsibilities", 0.7),
    ("function_descriptions", 0.65),
    ("data_flow_diagram", 0.6),

    # Priority 4: Extended content
    ("implementation_notes", 0.4),
    ("code_examples", 0.35),
    ("edge_cases", 0.3),

    # Priority 5 (lowest): Trim first
    ("internal_helpers", 0.2),
    ("deprecated_apis", 0.1),
    ("historical_notes", 0.05),
]

def prioritize_content(content_items: list, budget: int) -> list:
    """
    Select content items to fit within token budget.
    Uses greedy selection by priority score.
    """
    # Score each item
    scored_items = []
    for item in content_items:
        priority = CONTENT_PRIORITY.get(item.type, 0.5)
        score = priority / max(item.token_count, 1)  # Value per token
        scored_items.append((score, item))

    # Sort by score descending
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Greedy selection
    selected = []
    used_tokens = 0
    for score, item in scored_items:
        if used_tokens + item.token_count <= budget:
            selected.append(item)
            used_tokens += item.token_count

    return selected
```

### 4.5 Cross-Layer Information Passing

Parent documents must *summarize* child documents to enable progressive disclosure:

```python
def generate_parent_summary(child_doc: Document, max_tokens: int = 200) -> str:
    """
    Generate a concise summary of child document for parent's navigation.

    Format: One paragraph (3-5 sentences) covering:
    1. What the child module/component does
    2. Key public interfaces (2-3 most important)
    3. When to dive deeper
    """
    summary_template = """
{child_name} handles {responsibility}.
Key interfaces: {top_3_interfaces}.
Dive deeper when: {dive_condition}.
"""
    # Extract key info from child document
    responsibility = child_doc.description
    top_interfaces = child_doc.public_interfaces[:3]
    dive_condition = f"working with {child_doc.primary_concept}"

    summary = summary_template.format(
        child_name=child_doc.name,
        responsibility=responsibility,
        top_3_interfaces=", ".join(top_interfaces),
        dive_condition=dive_condition
    )

    # Truncate if needed
    if estimate_tokens(summary) > max_tokens:
        summary = truncate_to_budget(summary, max_tokens)

    return summary
```

---

## 5. Recursive Termination Conditions

### 5.1 When to Stop Generating Deeper Documents

The recursion stops when **any** of these conditions is met:

```python
def should_terminate_recursion(
    current_depth: int,
    metrics: ModuleMetrics,
    parent_budget: int,
    config: DocumentConfig
) -> tuple[bool, str]:
    """
    Determine if recursion should terminate.

    Returns: (should_stop, reason)
    """

    # CONDITION 1: Maximum depth reached
    if current_depth >= config.max_depth:
        return True, f"max_depth_reached ({config.max_depth})"

    # CONDITION 2: Module too small to split
    if metrics.line_count < config.min_lines_per_doc:
        return True, f"below_min_lines ({metrics.line_count} < {config.min_lines_per_doc})"

    # CONDITION 3: Token budget exhausted
    if parent_budget < config.min_budget_per_doc:
        return True, f"budget_exhausted ({parent_budget} < {config.min_budget_per_doc})"

    # CONDITION 4: No meaningful split possible
    if not can_split_meaningfully(metrics, config):
        return True, "no_meaningful_split"

    # CONDITION 5: Utility module depth limit
    if metrics.is_utility_module and current_depth >= 2:
        return True, "utility_module_depth_limit"

    # CONDITION 6: Single file with no internal structure
    if metrics.file_count == 1 and metrics.class_count <= 1:
        return True, "single_unit_file"

    return False, ""
```

### 5.2 Definition of Minimum Documentable Unit

```python
@dataclass
class MinimumDocumentableUnit:
    """
    Thresholds below which no separate document is created.
    Instead, content is merged into parent document.
    """
    min_lines: int = 30
    min_functions: int = 2
    min_classes: int = 1
    min_tokens: int = 200
    min_complexity_score: float = 5.0

    def is_documentable(self, metrics: ModuleMetrics) -> bool:
        """
        Check if unit meets minimum thresholds for documentation.
        """
        checks = [
            metrics.line_count >= self.min_lines,
            metrics.estimated_tokens >= self.min_tokens,
            metrics.function_count >= self.min_functions or
            metrics.class_count >= self.min_classes,
        ]
        return all(checks)
```

### 5.3 Merge Strategy for Small Units

When a unit is too small for a separate document:

```python
def merge_small_unit_into_parent(
    unit_metrics: ModuleMetrics,
    parent_doc: Document,
    merge_position: str = "inline"  # "inline" | "appendix" | "summary"
) -> None:
    """
    Merge a small unit's content into its parent document.

    merge_position:
    - "inline": Add as a subsection in the parent's body
    - "appendix": Add to a "Related Components" section
    - "summary": Add just a one-liner to the module list
    """
    if unit_metrics.line_count < 15:
        # Very tiny: just a summary line
        merge_position = "summary"
    elif unit_metrics.line_count < 50:
        # Small: appendix section
        merge_position = "appendix"

    if merge_position == "summary":
        parent_doc.add_module_entry(
            name=unit_metrics.name,
            description=unit_metrics.one_liner,
            link=None  # No separate doc
        )
    elif merge_position == "appendix":
        parent_doc.add_appendix_section(
            title=f"Related: {unit_metrics.name}",
            content=generate_compact_description(unit_metrics)
        )
    else:  # inline
        parent_doc.add_subsection(
            title=unit_metrics.name,
            content=generate_inline_content(unit_metrics)
        )
```

---

## 6. Flask Project Validation

### 6.1 Flask Structure Analysis

Flask (src/flask/) has the following characteristics:

```
src/flask/
├── sansio/           # Subdirectory (Sans-I/O async support)
├── json/             # Subdirectory (JSON handling)
├── __init__.py
├── app.py            # Flask application class
├── blueprints.py     # Blueprint support
├── cli.py            # CLI commands
├── config.py         # Configuration
├── ctx.py            # Request context
├── debughelpers.py   # Debug utilities
├── globals.py        # Global objects
├── helpers.py        # Helper functions
├── logging.py        # Logging configuration
├── sansio_scaffold.py # Sans-I/O scaffold
├── sessions.py       # Session management
├── signals.py        # Signal support
├── templating.py     # Template helpers
├── testing.py        # Testing utilities
├── views.py          # Class-based views
├── wrapping.py       # Request wrapping
└── ... (24 files total, ~7,700 LOC)
```

### 6.2 Applying the Depth Algorithm

```python
# Flask module metrics
flask_metrics = ModuleMetrics(
    file_count=24,
    function_count=150,      # Estimated
    class_count=25,          # Estimated
    line_count=7700,
    estimated_tokens=7700 * 4,  # ~30,800 tokens (Python: ~4 chars/token)
    subpackage_count=2,      # sansio/, json/
    dependency_count=40,     # Estimated
    cyclomatic_complexity=3.5,
    is_utility_module=False,
    has_clear_entry_point=True  # Flask class in app.py
)

# Calculate depth
structural_depth = _calc_structural_depth(2)  # subpackage_count=2 -> depth 1
complexity_depth = _calc_complexity_depth(150, 25, 7700, 3.5)
# complexity_score = 150*1 + 25*3 + 7700/100 + 3.5*2 = 150 + 75 + 77 + 7 = 309
# complexity_score=309 -> depth 4

token_depth = _calc_token_depth(30800)
# estimated_tokens=30800 -> depth 4

final_depth = max(1, 4, 4) = 4
```

### 6.3 Expected Document Tree for Flask

Based on depth=4 and SUBPACKAGE split strategy:

```
docs/flask/
├── INDEX.md                           # Level 0: Flask package overview
│   ├── What Flask does
│   ├── Architecture diagram (all components)
│   ├── Module list with links
│   └── Entry points (Flask class)
│
├── OVERVIEW.md                        # Level 1: Core Flask module
│   ├── Detailed module description
│   ├── Dependency graph
│   ├── Public API summary
│   └── Submodule navigation
│
├── sansio/
│   ├── OVERVIEW.md                    # Level 2: Sans-I/O submodule
│   │   ├── What sansio provides
│   │   └── Component list
│   └── app.py (ARCHITECTURE.md)       # Level 3: SansIOApp details
│
├── json/
│   ├── OVERVIEW.md                    # Level 2: JSON submodule
│   └── tag.py (ARCHITECTURE.md)       # Level 3: Tagged JSON details
│
├── app.py (ARCHITECTURE.md)           # Level 2: Flask class details
│   ├── Class structure
│   ├── Core methods (run, route, etc.)
│   └── Request lifecycle
│
├── blueprints.py (ARCHITECTURE.md)    # Level 2: Blueprint system
│
├── ctx.py (ARCHITECTURE.md)           # Level 2: Request context
│
├── sessions.py (ARCHITECTURE.md)      # Level 2: Session management
│
├── views.py (ARCHITECTURE.md)         # Level 2: Class-based views
│
└── [merged sections for smaller files]
    ├── helpers.py, debughelpers.py, globals.py
    │   -> Merged into parent OVERVIEW.md as "Utilities" section
    └── config.py, logging.py, signals.py
        -> Merged as "Configuration & Support" section
```

### 6.4 Depth Decisions Explained

| Component | Metrics | Depth | Split Strategy | Reasoning |
|-----------|---------|-------|----------------|-----------|
| **flask/ (root)** | 24 files, 7700 LOC, 2 subpackages | 4 | SUBPACKAGE | Large package with clear substructure |
| **sansio/** | 4 files, ~800 LOC | 2 | FILE | Small subpackage, flat structure |
| **json/** | 3 files, ~400 LOC | 1 | FILE | Tiny subpackage, merged docs |
| **app.py** | ~1000 LOC, Flask class | 2 | N/A (leaf) | Single large file, detailed doc |
| **blueprints.py** | ~500 LOC | 2 | N/A (leaf) | Medium file, detailed doc |
| **helpers.py** | ~200 LOC | 0 | N/A | Too small, merged into parent |

### 6.5 Token Budget Distribution

```
Total budget for Flask: 30,800 * 0.15 * (1 + 4*0.5) = 30,800 * 0.15 * 3.0 = 13,860 tokens

Allocation:
├── Level 0 (INDEX.md):            3,500 tokens (25%)
├── Level 1 (OVERVIEW.md):         3,000 tokens (22%)
├── Level 2 (8 subdocuments):      5,500 tokens (40%) ~ 690 each
└── Level 3 (4 subdocuments):      1,860 tokens (13%) ~ 465 each
```

---

## 7. Implementation Pseudocode

### 7.1 Main Entry Point

```python
def plan_documentation(
    module_metrics: ModuleMetrics,
    config: DocumentConfig = DocumentConfig()
) -> DocumentPlan:
    """
    Main entry point for documentation planning.

    Given module metrics, produce a complete documentation plan.
    """
    # Step 1: Calculate depth
    depth = calculate_depth(module_metrics)

    # Step 2: Determine if module should be merged into parent
    should_merge = (
        depth == 0 or
        module_metrics.line_count < config.min_lines_for_standalone
    )

    if should_merge:
        return DocumentPlan(
            depth=0,
            split_strategy=SplitStrategy.NONE,
            doc_budget_per_level=[300],
            should_merge_parent=True,
            termination_reason="below_minimum_size"
        )

    # Step 3: Select split strategy
    split_strategy = select_split_strategy(module_metrics)

    # Step 4: Calculate token budget
    total_budget = calculate_total_budget(module_metrics, depth)
    budget_per_level = allocate_budget_per_level(total_budget, depth)

    # Step 5: Plan subdocuments (if depth > 1)
    subdocuments = []
    if depth >= 2:
        subdocuments = plan_subdocuments(
            module_metrics,
            split_strategy,
            budget_per_level[1:],
            current_depth=1,
            config=config
        )

    return DocumentPlan(
        depth=depth,
        split_strategy=split_strategy,
        doc_budget_per_level=budget_per_level,
        should_merge_parent=False,
        termination_reason="" if depth > 0 else "merged",
        subdocuments=subdocuments
    )
```

### 7.2 Recursive Subdocument Planning

```python
def plan_subdocuments(
    parent_metrics: ModuleMetrics,
    split_strategy: SplitStrategy,
    remaining_budgets: list[int],
    current_depth: int,
    config: DocumentConfig
) -> list[DocumentPlan]:
    """
    Recursively plan subdocuments based on split strategy.
    """
    # Check termination
    should_stop, reason = should_terminate_recursion(
        current_depth,
        parent_metrics,
        remaining_budgets[0] if remaining_budgets else 0,
        config
    )
    if should_stop:
        return []

    # Get subunits based on strategy
    if split_strategy == SplitStrategy.SUBPACKAGE:
        subunits = get_subpackage_units(parent_metrics)
    elif split_strategy == SplitStrategy.CLASS:
        subunits = get_class_units(parent_metrics)
    elif split_strategy == SplitStrategy.FUNCTION_GROUP:
        subunits = get_function_group_units(parent_metrics)
    else:
        subunits = get_file_units(parent_metrics)

    # Filter to documentable units
    documentable_units = [
        u for u in subunits
        if MINIMUM_DOCUMENTABLE_UNIT.is_documentable(u)
    ]

    # Allocate budget proportionally
    total_size = sum(u.line_count for u in documentable_units)
    subdocument_plans = []

    for unit in documentable_units:
        unit_budget_share = unit.line_count / total_size
        unit_budgets = [int(b * unit_budget_share) for b in remaining_budgets]

        # Recursively plan this subdocument
        sub_plan = plan_documentation(
            unit,
            config=config.with_budget_override(unit_budgets[0])
        )
        subdocument_plans.append(sub_plan)

    return subdocument_plans
```

---

## 8. Configuration Reference

### 8.1 Full Configuration Schema

```yaml
# doc-config.yaml

document_generation:
  # Depth control
  max_depth: 5
  min_depth: 0

  # Minimum sizes for standalone documents
  min_lines_for_standalone: 100
  min_functions_for_standalone: 3
  min_tokens_for_standalone: 500

  # Minimum documentable unit (below this, merge into parent)
  min_lines_per_doc: 30
  min_tokens_per_doc: 200

  # Budget settings
  base_budget_ratio: 0.15        # Documentation tokens / source tokens
  depth_multiplier: 0.5          # Additional budget per depth level
  utility_budget_factor: 0.6     # Reduce budget for utility modules

  # Budget minimums per level
  min_budget_per_level:
    0: 800
    1: 1200
    2: 2000
    3: 1500
    4: 1500
    5: 1500

  # Complexity thresholds for depth calculation
  complexity_thresholds:
    depth_0: 10
    depth_1: 30
    depth_2: 100
    depth_3: 300
    depth_4: 600
    # depth_5: anything above

  # Token thresholds for depth calculation
  token_thresholds:
    depth_0: 500
    depth_1: 2000
    depth_2: 8000
    depth_3: 32000
    depth_4: 128000
    # depth_5: anything above

  # Split strategy preferences
  prefer_subpackage_split: true
  min_subpackage_balance: 0.4    # Largest subpackage must be < 60% of total

  # Content prioritization (higher = keep first when budget constrained)
  content_priority:
    module_name: 1.0
    description: 1.0
    public_interfaces: 0.9
    dependencies: 0.8
    architecture_diagram: 0.75
    class_details: 0.6
    function_details: 0.5
    examples: 0.3
    internal_notes: 0.2
```

### 8.2 Environment Variable Overrides

```bash
# Override configuration via environment variables
export DOC_MAX_DEPTH=4
export DOC_MIN_LINES=50
export DOC_BUDGET_RATIO=0.20
export DOC_UTILITY_FACTOR=0.5
```

---

## Appendix A: Decision Flowchart

```
                    ┌─────────────────────────┐
                    │   Module Metrics Input   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Calculate Depth Score   │
                    │  (structural + complexity│
                    │   + token)               │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   depth == 0 OR         │
                    │   below min size?       │
                    └────────────┬────────────┘
                          │            │
                        Yes            No
                          │            │
                          ▼            ▼
                   ┌──────────┐  ┌─────────────────┐
                   │  Merge   │  │ Select Split    │
                   │  into    │  │ Strategy        │
                   │  parent  │  │ (subpackage >   │
                   └──────────┘  │ class > func >  │
                                 │ file)           │
                                 └────────┬────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │ Allocate Token Budget │
                              │ (per level)           │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │ For each subunit:     │
                              │ - Check min size      │
                              │ - Recurse if viable   │
                              │ - Merge if too small  │
                              └───────────────────────┘
```

---

## Appendix B: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│           DYNAMIC DEPTH DECISION QUICK REFERENCE                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DEPTH CALCULATION                                              │
│  ─────────────────                                              │
│  depth = max(structural_depth, complexity_depth, token_depth)  │
│                                                                 │
│  Structural: 0 (flat) to 5 (20+ subpackages)                   │
│  Complexity: 0 (score<10) to 5 (score>600)                     │
│  Token:      0 (<500) to 5 (>128K tokens)                      │
│                                                                 │
│  SPLIT STRATEGY SELECTION                                       │
│  ─────────────────────────                                      │
│  1. SUBPACKAGE  if 2+ balanced subpackages                      │
│  2. CLASS       if 3+ classes, OOP-heavy                        │
│  3. FUNCTION    if 5+ functions, functional style               │
│  4. HYBRID      if mixed structure                              │
│  5. FILE        fallback                                        │
│                                                                 │
│  MINIMUM DOCUMENTABLE UNIT                                      │
│  ────────────────────────                                       │
│  - 30+ lines                                                    │
│  - 2+ functions OR 1+ class                                     │
│  - 200+ tokens                                                  │
│  Below threshold -> merge into parent                           │
│                                                                 │
│  BUDGET ALLOCATION                                              │
│  ─────────────────                                              │
│  Total = source_tokens × 0.15 × (1 + depth × 0.5)              │
│  Per level: Geometric decay (60% per level)                     │
│  Level 0: min 800 tokens                                        │
│  Level 1: min 1200 tokens                                       │
│  Level 2: min 2000 tokens                                       │
│                                                                 │
│  TERMINATION CONDITIONS                                         │
│  ───────────────────────                                        │
│  ✓ depth >= max_depth (5)                                       │
│  ✓ lines < min_lines (30)                                       │
│  ✓ budget < min_budget (200)                                    │
│  ✓ utility module at depth 2                                    │
│  ✓ single file, single class                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Appendix C: Algorithm Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| `calculate_depth()` | O(1) | O(1) |
| `select_split_strategy()` | O(n) where n = file count | O(1) |
| `plan_subdocuments()` | O(n × m) where n = units, m = max depth | O(d) recursion depth |
| `allocate_budget_per_level()` | O(d) where d = depth | O(d) |
| Full planning for module | O(n × d) | O(n × d) |

For a typical project with 1000 files and average depth 3:
- Time: O(1000 × 3) = O(3000) operations
- Space: O(1000 × 3) = O(3000) plan entries

This is highly efficient and suitable for real-time documentation generation.

---

*End of Document*
