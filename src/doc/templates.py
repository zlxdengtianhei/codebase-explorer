"""Jinja2 template loading and rendering engine.

Loads ``.j2`` template files from the ``src/templates/`` directory
(or a custom path) and provides typed rendering methods for each
document level.

Custom Jinja2 filters:
- ``slugify``: Convert a string to a URL-safe slug.
- ``truncate``: Truncate a string with ellipsis.
- ``format_complexity``: Map a float score to Low/Medium/High/Critical.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


# ---------------------------------------------------------------------------
# Custom Jinja2 filters
# ---------------------------------------------------------------------------


def _slugify(value: str) -> str:
    """Convert a string to a URL-safe slug."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")


def _format_complexity(score: float) -> str:
    """Map a normalised complexity score to a human-readable label."""
    if score < 0.25:
        return "Low"
    if score < 0.50:
        return "Medium"
    if score < 0.75:
        return "High"
    return "Critical"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TemplateRenderer:
    """Loads and renders Jinja2 documentation templates.

    Attributes:
        env: The Jinja2 ``Environment`` used for template loading.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialise the template renderer.

        Args:
            templates_dir: Directory containing ``.j2`` templates.
                Defaults to ``src/templates/``.
        """
        resolved_dir = templates_dir or _DEFAULT_TEMPLATES_DIR

        if not resolved_dir.is_dir():
            logger.warning(
                "Templates directory does not exist: %s", resolved_dir
            )

        self.env = Environment(
            loader=FileSystemLoader(str(resolved_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register custom filters
        self.env.filters["slugify"] = _slugify
        self.env.filters["format_complexity"] = _format_complexity

    # -- Level-specific rendering ------------------------------------------

    def render_index(self, context: dict) -> str:
        """Render the Level 0 INDEX.md template.

        Args:
            context: Template variables (project, modules, diagram, etc.).

        Returns:
            Rendered markdown string.
        """
        return self._render("index.md.j2", context)

    def render_overview(self, context: dict) -> str:
        """Render the Level 1 OVERVIEW.md template.

        Args:
            context: Template variables (module, files, interfaces, etc.).

        Returns:
            Rendered markdown string.
        """
        return self._render("overview.md.j2", context)

    def render_detail(self, context: dict) -> str:
        """Render the Level 2+ DETAIL.md template.

        This template is universal and works at any depth >= 2.

        Args:
            context: Template variables (document, classes, functions, etc.).

        Returns:
            Rendered markdown string.
        """
        return self._render("detail.md.j2", context)

    # -- Generic rendering -------------------------------------------------

    def render(self, template_name: str, context: dict) -> str:
        """Render an arbitrary template by name.

        Args:
            template_name: The template file name (e.g. ``index.md.j2``).
            context: Template variable mapping.

        Returns:
            Rendered string.

        Raises:
            TemplateNotFound: If the template file does not exist.
        """
        return self._render(template_name, context)

    def get_template_names(self) -> list[str]:
        """List all available template names.

        Returns:
            Sorted list of template file names.
        """
        return sorted(self.env.loader.list_templates())  # type: ignore[union-attr]

    # -- Internal ----------------------------------------------------------

    def _render(self, template_name: str, context: dict) -> str:
        """Load and render a template with the given context."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            logger.error("Template not found: %s", template_name)
            raise
        except Exception:
            logger.error(
                "Failed to render template %s", template_name, exc_info=True
            )
            raise
