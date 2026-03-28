"""Per-repo ground truth definitions for semantic correctness validation.

Complements the mechanised scoring harness by providing human-curated
expectations about where specific files should (or should not) be classified.

Each repo entry can specify:
  - must_be_infra: files that should be in infrastructure_nodes
  - must_not_be_infra: files that should NOT be in infrastructure_nodes
  - must_be_same_cone: pairs of files that should be in the same cone
  - must_be_separate_cones: directory groups that should form separate cones
"""

from __future__ import annotations

import fnmatch
import posixpath
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Ground Truth Definitions
# ---------------------------------------------------------------------------

GROUND_TRUTH: dict[str, dict] = {
    "rich": {
        "must_be_infra": [
            "rich/console.py",         # Core rendering engine, used by all
            "rich/text.py",            # Base text type
            "rich/style.py",           # Style system foundation
            "rich/segment.py",         # Render segment foundation
            "rich/color.py",           # Color system foundation
            "rich/_cell_widths.py",    # Low-level utility data
        ],
        "must_not_be_infra": [
            "rich/markdown.py",        # Feature module: Markdown rendering
            "rich/table.py",           # Feature module: Table rendering
            "rich/progress.py",        # Feature module: Progress bars
            "rich/tree.py",            # Feature module: Tree rendering
            "rich/syntax.py",          # Feature module: Syntax highlighting
            "rich/panel.py",           # Feature module: Panel rendering
        ],
        "must_be_same_cone": [
            ("rich/markdown.py", "rich/markup.py"),
        ],
    },
    "fastapi": {
        "must_be_infra": [
            "fastapi/_compat.py",      # Compatibility utilities
        ],
        "must_not_be_infra": [
            "fastapi/security/*.py",   # Security modules are features
            "fastapi/middleware/*.py",  # Middleware modules are features
        ],
        "must_be_separate_cones": [
            "fastapi/security",        # Security should be its own group
            "fastapi/middleware",       # Middleware should be its own group
        ],
    },
    "scrapy": {
        "must_be_infra": [
            "scrapy/exceptions.py",
            "scrapy/utils/*.py",
        ],
        "must_not_be_infra": [
            "scrapy/spidermiddlewares/*.py",
            "scrapy/downloadermiddlewares/*.py",
            "scrapy/commands/*.py",
        ],
    },
    "celery": {
        "must_be_infra": [
            "celery/utils/*.py",       # Utility code
            "celery/exceptions.py",
        ],
        "must_not_be_infra": [
            "celery/beat.py",          # Scheduled tasks — feature module
            "celery/canvas.py",        # Task composition — feature module
            "celery/result.py",        # Result backend — feature module
        ],
    },
    "flask": {
        "must_be_infra": [
            "src/flask/globals.py",    # Global state
            "src/flask/helpers.py",    # Helper utilities
        ],
        "must_not_be_infra": [
            "src/flask/blueprints.py", # Feature: Blueprints
            "src/flask/views.py",      # Feature: Views
            "src/flask/testing.py",    # Feature: Testing utilities
        ],
    },
}


# ---------------------------------------------------------------------------
# Cluster Ground Truth — file→group labels for ARI-based validation
# ---------------------------------------------------------------------------
# Maps repo_name -> { relative_file_path: "group-label" }.
# File paths use posix-style relative paths matching cone.exclusive_files.
# Only files whose group membership is clear and unambiguous are included.
# Infrastructure files are labeled "__infra__".

CLUSTER_GROUND_TRUTH: dict[str, dict[str, str]] = {
    "celery": {
        # task-execution
        "celery/app/task.py": "task-execution",
        "celery/app/trace.py": "task-execution",
        "celery/app/builtins.py": "task-execution",
        "celery/app/registry.py": "task-execution",
        "celery/app/autoretry.py": "task-execution",
        "celery/result.py": "task-execution",
        # canvas
        "celery/canvas.py": "canvas",
        # transport
        "celery/app/amqp.py": "transport",
        "celery/app/routes.py": "transport",
        # backends
        "celery/backends/base.py": "backends",
        "celery/backends/redis.py": "backends",
        "celery/backends/cache.py": "backends",
        "celery/backends/rpc.py": "backends",
        "celery/backends/mongodb.py": "backends",
        "celery/backends/filesystem.py": "backends",
        # worker
        "celery/worker/worker.py": "worker",
        "celery/worker/strategy.py": "worker",
        "celery/worker/request.py": "worker",
        "celery/worker/state.py": "worker",
        "celery/worker/autoscale.py": "worker",
        "celery/apps/worker.py": "worker",
        # consumer
        "celery/worker/consumer/consumer.py": "consumer",
        "celery/worker/consumer/connection.py": "consumer",
        "celery/worker/consumer/tasks.py": "consumer",
        "celery/worker/consumer/events.py": "consumer",
        # beat
        "celery/beat.py": "beat",
        "celery/schedules.py": "beat",
        "celery/apps/beat.py": "beat",
        # events
        "celery/events/__init__.py": "events",
        "celery/events/dispatcher.py": "events",
        "celery/events/receiver.py": "events",
        "celery/events/state.py": "events",
        "celery/events/snapshot.py": "events",
        # cli
        "celery/bin/celery.py": "cli",
        "celery/bin/worker.py": "cli",
        "celery/bin/beat.py": "cli",
        "celery/bin/events.py": "cli",
        "celery/bin/control.py": "cli",
        "celery/bin/multi.py": "cli",
        # security
        "celery/security/__init__.py": "security",
        "celery/security/serialization.py": "security",
        "celery/security/certificate.py": "security",
        "celery/security/key.py": "security",
        # __infra__
        "celery/app/base.py": "__infra__",
        "celery/app/utils.py": "__infra__",
        "celery/_state.py": "__infra__",
        "celery/local.py": "__infra__",
        "celery/bootsteps.py": "__infra__",
        "celery/signals.py": "__infra__",
        "celery/exceptions.py": "__infra__",
        "celery/platforms.py": "__infra__",
        "celery/utils/log.py": "__infra__",
        "celery/utils/functional.py": "__infra__",
        "celery/utils/time.py": "__infra__",
        "celery/utils/collections.py": "__infra__",
        "celery/utils/imports.py": "__infra__",
    },
    "fastapi": {
        # routing
        "fastapi/applications.py": "routing",
        "fastapi/routing.py": "routing",
        # dependency-injection
        "fastapi/dependencies/utils.py": "dependency-injection",
        "fastapi/dependencies/models.py": "dependency-injection",
        "fastapi/params.py": "dependency-injection",
        "fastapi/param_functions.py": "dependency-injection",
        # openapi
        "fastapi/openapi/utils.py": "openapi",
        "fastapi/openapi/models.py": "openapi",
        "fastapi/openapi/docs.py": "openapi",
        "fastapi/openapi/constants.py": "openapi",
        # security
        "fastapi/security/__init__.py": "security",
        "fastapi/security/api_key.py": "security",
        "fastapi/security/http.py": "security",
        "fastapi/security/oauth2.py": "security",
        "fastapi/security/open_id_connect_url.py": "security",
        # middleware
        "fastapi/middleware/cors.py": "middleware",
        "fastapi/middleware/gzip.py": "middleware",
        "fastapi/middleware/httpsredirect.py": "middleware",
        "fastapi/middleware/trustedhost.py": "middleware",
        # request-response
        "fastapi/requests.py": "request-response",
        "fastapi/responses.py": "request-response",
        "fastapi/encoders.py": "request-response",
        "fastapi/exception_handlers.py": "request-response",
        "fastapi/exceptions.py": "request-response",
        # websocket
        "fastapi/websockets.py": "websocket",
        # __infra__
        "fastapi/_compat/shared.py": "__infra__",
        "fastapi/utils.py": "__infra__",
        "fastapi/logger.py": "__infra__",
        "fastapi/types.py": "__infra__",
        "fastapi/datastructures.py": "__infra__",
    },
    "flask": {
        # app-core
        "src/flask/app.py": "app-core",
        "src/flask/sansio/app.py": "app-core",
        "src/flask/sansio/scaffold.py": "app-core",
        # routing
        "src/flask/views.py": "routing",
        "src/flask/wrappers.py": "routing",
        # blueprints
        "src/flask/blueprints.py": "blueprints",
        "src/flask/sansio/blueprints.py": "blueprints",
        # context
        "src/flask/ctx.py": "context",
        "src/flask/globals.py": "context",
        # sessions
        "src/flask/sessions.py": "sessions",
        # templating
        "src/flask/templating.py": "templating",
        # json
        "src/flask/json/__init__.py": "json",
        "src/flask/json/provider.py": "json",
        "src/flask/json/tag.py": "json",
        # cli
        "src/flask/cli.py": "cli",
        # testing
        "src/flask/testing.py": "testing",
        # __infra__
        "src/flask/helpers.py": "__infra__",
        "src/flask/signals.py": "__infra__",
        "src/flask/logging.py": "__infra__",
        "src/flask/typing.py": "__infra__",
        "src/flask/debughelpers.py": "__infra__",
        "src/flask/config.py": "__infra__",
    },
    "rich": {
        # styling
        "rich/style.py": "styling",
        "rich/color.py": "styling",
        "rich/color_triplet.py": "styling",
        "rich/palette.py": "styling",
        "rich/theme.py": "styling",
        "rich/terminal_theme.py": "styling",
        "rich/default_styles.py": "styling",
        # text-processing
        "rich/markup.py": "text-processing",
        "rich/highlighter.py": "text-processing",
        "rich/emoji.py": "text-processing",
        "rich/cells.py": "text-processing",
        # layout
        "rich/layout.py": "layout",
        "rich/columns.py": "layout",
        "rich/panel.py": "layout",
        "rich/align.py": "layout",
        "rich/padding.py": "layout",
        "rich/box.py": "layout",
        "rich/rule.py": "layout",
        "rich/constrain.py": "layout",
        # data-widgets
        "rich/table.py": "data-widgets",
        "rich/tree.py": "data-widgets",
        "rich/markdown.py": "data-widgets",
        "rich/syntax.py": "data-widgets",
        "rich/pretty.py": "data-widgets",
        "rich/json.py": "data-widgets",
        # progress
        "rich/live.py": "progress",
        "rich/progress.py": "progress",
        "rich/progress_bar.py": "progress",
        "rich/spinner.py": "progress",
        "rich/status.py": "progress",
        # logging
        "rich/logging.py": "logging",
        "rich/traceback.py": "logging",
        # interactive
        "rich/prompt.py": "interactive",
        "rich/pager.py": "interactive",
        # __infra__
        "rich/console.py": "__infra__",
        "rich/segment.py": "__infra__",
        "rich/text.py": "__infra__",
        "rich/errors.py": "__infra__",
        "rich/_ratio.py": "__infra__",
        "rich/_loop.py": "__infra__",
        "rich/protocol.py": "__infra__",
        "rich/abc.py": "__infra__",
        "rich/measure.py": "__infra__",
    },
    "scrapy": {
        # engine
        "scrapy/core/engine.py": "engine",
        "scrapy/core/scheduler.py": "engine",
        "scrapy/core/scraper.py": "engine",
        "scrapy/crawler.py": "engine",
        # downloader
        "scrapy/core/downloader/__init__.py": "downloader",
        "scrapy/core/downloader/middleware.py": "downloader",
        "scrapy/core/downloader/handlers/__init__.py": "downloader",
        # http-model
        "scrapy/http/request/__init__.py": "http-model",
        "scrapy/http/response/__init__.py": "http-model",
        "scrapy/http/response/html.py": "http-model",
        "scrapy/http/response/text.py": "http-model",
        "scrapy/http/headers.py": "http-model",
        "scrapy/http/cookies.py": "http-model",
        "scrapy/link.py": "http-model",
        # spiders
        "scrapy/spiders/__init__.py": "spiders",
        "scrapy/spiders/crawl.py": "spiders",
        "scrapy/spiders/sitemap.py": "spiders",
        "scrapy/spiders/feed.py": "spiders",
        "scrapy/spiderloader.py": "spiders",
        # selectors
        "scrapy/selector/__init__.py": "selectors",
        "scrapy/selector/unified.py": "selectors",
        "scrapy/linkextractors/__init__.py": "selectors",
        "scrapy/linkextractors/lxmlhtml.py": "selectors",
        # items-export
        "scrapy/item.py": "items-export",
        "scrapy/loader/__init__.py": "items-export",
        "scrapy/exporters.py": "items-export",
        "scrapy/pipelines/__init__.py": "items-export",
        "scrapy/pipelines/media.py": "items-export",
        "scrapy/pipelines/files.py": "items-export",
        "scrapy/pipelines/images.py": "items-export",
        # downloader-middlewares
        "scrapy/downloadermiddlewares/retry.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/redirect.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/cookies.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/httpcache.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/httpauth.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/httpcompression.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/useragent.py": "downloader-middlewares",
        "scrapy/downloadermiddlewares/defaultheaders.py": "downloader-middlewares",
        # spider-middlewares
        "scrapy/spidermiddlewares/depth.py": "spider-middlewares",
        "scrapy/spidermiddlewares/httperror.py": "spider-middlewares",
        "scrapy/spidermiddlewares/urllength.py": "spider-middlewares",
        "scrapy/spidermiddlewares/referer.py": "spider-middlewares",
        # extensions
        "scrapy/extensions/feedexport.py": "extensions",
        "scrapy/extensions/throttle.py": "extensions",
        "scrapy/extensions/corestats.py": "extensions",
        "scrapy/extensions/logstats.py": "extensions",
        "scrapy/extensions/memusage.py": "extensions",
        "scrapy/extensions/closespider.py": "extensions",
        "scrapy/statscollectors.py": "extensions",
        # cli
        "scrapy/cmdline.py": "cli",
        "scrapy/commands/crawl.py": "cli",
        "scrapy/commands/fetch.py": "cli",
        "scrapy/commands/shell.py": "cli",
        "scrapy/commands/genspider.py": "cli",
        "scrapy/commands/startproject.py": "cli",
        # __infra__
        "scrapy/settings/__init__.py": "__infra__",
        "scrapy/settings/default_settings.py": "__infra__",
        "scrapy/middleware.py": "__infra__",
        "scrapy/exceptions.py": "__infra__",
        "scrapy/signals.py": "__infra__",
        "scrapy/utils/misc.py": "__infra__",
        "scrapy/utils/defer.py": "__infra__",
        "scrapy/utils/url.py": "__infra__",
        "scrapy/utils/conf.py": "__infra__",
        "scrapy/utils/log.py": "__infra__",
    },
}


# ---------------------------------------------------------------------------
# Checking logic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroundTruthViolation:
    """A single ground truth violation."""

    repo: str
    rule_type: str          # must_be_infra | must_not_be_infra | must_be_same_cone | must_be_separate_cones
    file_or_group: str
    expected: str
    actual: str


def _match_files(pattern: str, all_files: set[str]) -> list[str]:
    """Match a glob pattern against a set of file paths."""
    return sorted(f for f in all_files if fnmatch.fnmatch(f, pattern))


def check_ground_truth(
    repo_name: str,
    cones: dict,
    infra_nodes: frozenset[str],
    all_files: set[str] | None = None,
) -> list[GroundTruthViolation]:
    """Check feature cones against ground truth expectations.

    Args:
        repo_name: Repository name (must match a key in GROUND_TRUTH).
        cones: Dict of cone_id -> FeatureCone.
        infra_nodes: Set of infrastructure file paths.
        all_files: Optional set of all file paths (for glob matching).

    Returns:
        List of violations found.
    """
    truth = GROUND_TRUTH.get(repo_name)
    if not truth:
        return []

    if all_files is None:
        all_files = set()
        for cone in cones.values():
            all_files.update(cone.exclusive_files)
        all_files.update(infra_nodes)

    # Build file -> cone_id map
    file_to_cone: dict[str, str] = {}
    for cone in cones.values():
        for f in cone.exclusive_files:
            file_to_cone[f] = cone.cone_id

    violations: list[GroundTruthViolation] = []

    # Check must_be_infra
    for pattern in truth.get("must_be_infra", []):
        matched = _match_files(pattern, all_files)
        for f in matched:
            if f not in infra_nodes:
                violations.append(GroundTruthViolation(
                    repo=repo_name,
                    rule_type="must_be_infra",
                    file_or_group=f,
                    expected="infra",
                    actual=f"cone:{file_to_cone.get(f, 'unknown')}",
                ))

    # Check must_not_be_infra
    for pattern in truth.get("must_not_be_infra", []):
        matched = _match_files(pattern, all_files)
        for f in matched:
            if f in infra_nodes:
                violations.append(GroundTruthViolation(
                    repo=repo_name,
                    rule_type="must_not_be_infra",
                    file_or_group=f,
                    expected="cone",
                    actual="infra",
                ))

    # Check must_be_same_cone
    for pair in truth.get("must_be_same_cone", []):
        if len(pair) != 2:
            continue
        a, b = pair
        cone_a = file_to_cone.get(a)
        cone_b = file_to_cone.get(b)
        if cone_a and cone_b and cone_a != cone_b:
            violations.append(GroundTruthViolation(
                repo=repo_name,
                rule_type="must_be_same_cone",
                file_or_group=f"{a} + {b}",
                expected=f"same cone",
                actual=f"{cone_a} vs {cone_b}",
            ))

    # Check must_be_separate_cones
    dirs = truth.get("must_be_separate_cones", [])
    if len(dirs) >= 2:
        dir_cones: dict[str, set[str]] = {}
        for d in dirs:
            cones_for_dir: set[str] = set()
            for f, cone_id in file_to_cone.items():
                if f.startswith(d + "/"):
                    cones_for_dir.add(cone_id)
            dir_cones[d] = cones_for_dir

        for i, d1 in enumerate(dirs):
            for d2 in dirs[i + 1:]:
                overlap = dir_cones.get(d1, set()) & dir_cones.get(d2, set())
                if overlap:
                    violations.append(GroundTruthViolation(
                        repo=repo_name,
                        rule_type="must_be_separate_cones",
                        file_or_group=f"{d1} vs {d2}",
                        expected="separate cones",
                        actual=f"shared cones: {sorted(overlap)[:3]}",
                    ))

    return violations
