# Flask Algorithm Optimization: Before vs After

## Summary

| Metric | Baseline (v1) | Optimized (v2) | Change |
|--------|--------------|----------------|--------|
| Total Files | 24 | 24 | -- |
| Total Cones | 2 | 5 | +3 (+150%) |
| Single-file Cones | 2 | 0 | -2 (-100%) |
| Single-file Ratio | 100.0% | 0.0% | -100pp |
| Max Cone Size | 1 file | 12 files | +11 (+1100%) |
| Max Cone Ratio | 4.2% | 50.0% | +45.8pp |
| Avg Cone Size | 1.0 | 4.8 | +3.8 (+380%) |
| Infrastructure Files | 22 (91.7%) | 0 (0.0%) | -22 (-100%) |
| Files Assigned to Cones | 2 (8.3%) | 24 (100%) | +22 (+1100%) |
| Avg Confidence Score | N/A | 0.4318 | NEW |

## Key Improvements

1. **File coverage: 8.3% -> 100%.** The baseline left 22 of 24 files (91.7%) unclassified as infrastructure because the naive shared-threshold classified every reachable node as shared. The optimized algorithm assigns all 24 files to meaningful cones.

2. **Single-file ratio: 100% -> 0%.** The baseline produced only 2 single-file cones (the two in-degree=0 roots). The optimized algorithm's orphan-merge rebalancing (T-06) groups single-file cones by directory, eliminating all single-file cones.

3. **Cone count: 2 -> 5.** The optimized algorithm detects more structure by using affinity-decay BFS (T-04) to trace dependencies with varying strength, then rebalances to produce 5 semantically coherent groups.

4. **Max cone size: 1 -> 12 files.** The largest cone (`dir::flask`) contains the 12 core Flask application files, representing a meaningful "core application" feature group.

## Cone Details (Optimized)

### Cone 1: `dir::flask` (12 files, 50,551 tokens, confidence: 0.2233)
Core Flask application module -- the largest cone containing the main app, blueprints, context, sessions, templating, and related functionality.
- `flask/app.py` (18,692 tokens) -- Main Flask application class
- `flask/blueprints.py` (1,595 tokens) -- Blueprint registration
- `flask/config.py` (3,776 tokens) -- Configuration handling
- `flask/ctx.py` (5,172 tokens) -- Application/request context
- `flask/debughelpers.py` (1,734 tokens) -- Debug utilities
- `flask/helpers.py` (7,039 tokens) -- Helper functions
- `flask/logging.py` (592 tokens) -- Logging setup
- `flask/sessions.py` (2,651 tokens) -- Session management
- `flask/signals.py` (679 tokens) -- Signal support
- `flask/templating.py` (2,184 tokens) -- Template rendering
- `flask/testing.py` (4,276 tokens) -- Test client utilities
- `flask/wrappers.py` (2,096 tokens) -- Request/Response wrappers

### Cone 2: `dir::flask/sansio` (3 files, 27,646 tokens, confidence: 0.52)
Sans-IO (protocol-only) layer -- framework logic without I/O dependencies.
- `flask/sansio/app.py` (8,675 tokens) -- Sans-IO application base
- `flask/sansio/blueprints.py` (7,719 tokens) -- Sans-IO blueprint base
- `flask/sansio/scaffold.py` (11,252 tokens) -- Scaffold base class

### Cone 3: `flask/__main__.py` (2 files, 10,524 tokens, confidence: 0.605)
CLI entry point -- the `__main__` module and the full CLI implementation.
- `flask/__main__.py` (214 tokens) -- Entry point
- `flask/cli.py` (10,310 tokens) -- Click-based CLI commands

### Cone 4: `dir::flask/json` (3 files, 6,430 tokens, confidence: 0.4033)
JSON serialization subsystem.
- `flask/json/__init__.py` (1,297 tokens) -- JSON module init
- `flask/json/provider.py` (2,889 tokens) -- JSON provider interface
- `flask/json/tag.py` (2,184 tokens) -- Tagged JSON serialization

### Cone 5: `flask/views.py` (4 files, 4,159 tokens, confidence: 0.4075)
View layer plus package-level exports and type definitions.
- `flask/__init__.py` (689 tokens) -- Package exports
- `flask/globals.py` (1,989 tokens) -- Global proxies (g, request, session)
- `flask/typing.py` (592 tokens) -- Type aliases
- `flask/views.py` (2,687 tokens) -- Class-based views

## Confidence Score Distribution

| Cone | Confidence | Interpretation |
|------|-----------|----------------|
| `flask/__main__.py` | 0.605 | High -- tight entry-point-to-CLI coupling |
| `dir::flask/sansio` | 0.520 | Medium-high -- cohesive sans-IO subpackage |
| `flask/views.py` | 0.408 | Medium -- views + related utility files |
| `dir::flask/json` | 0.403 | Medium -- self-contained JSON subpackage |
| `dir::flask` | 0.223 | Lower -- large merged cone dilutes avg affinity |
| **Average** | **0.432** | -- |

The lower confidence of `dir::flask` (0.223) reflects that this cone was formed by orphan-merge: 12 originally single-file cones in the `flask/` root directory were merged into one group. Individual affinity scores decay over distance from the cone entry point, and the merged cone's average is dragged down by peripherally-connected files.

## Analysis

### What the optimizations achieved

The V2 algorithm with Phase 2 optimizations (T-04 through T-06) transforms Flask analysis from "almost entirely infrastructure" to "fully classified into 5 feature groups":

- **T-04 (Weight-aware affinity-decay BFS):** By decaying affinity at each hop and weighting by edge type (import=0.3, call=0.5, inherit=0.7), the algorithm avoids the baseline's problem of every root reaching every file with equal weight. Files that are loosely connected fall below the affinity cutoff.

- **T-05 (Dynamic shared threshold):** With `max(2, round(5 * 0.3)) = 2`, the shared threshold adapts to the number of roots. For Flask's 2 in-degree=0 roots (expanded to more via library fallback), this prevents over-aggressive infrastructure classification.

- **T-06 (Rebalance -- orphan merge):** The 18 single-file orphan cones produced by affinity-decay BFS are merged by directory into 3 larger cones (`dir::flask`, `dir::flask/json`, `dir::flask/sansio`), eliminating 100% of single-file cones.

### Remaining considerations

1. The `dir::flask` cone at 12 files (50% of codebase) is at the mega-cone threshold but not above it, so it was not split further. A future refinement could lower the mega-cone threshold or use sub-directory heuristics within flat packages.

2. Infrastructure files dropped to 0 -- this may be overly aggressive for a library codebase where some files (like `globals.py`, `typing.py`) genuinely serve as shared infrastructure. The current algorithm classifies them within cones because fewer than 2 cones claim them.

3. Confidence scores provide a useful quality signal. Cones with higher confidence (>0.5) like `flask/__main__.py` and `dir::flask/sansio` represent tighter feature groups, while the merged `dir::flask` cone's lower score (0.22) correctly flags it as a looser grouping.
