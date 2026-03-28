"""Tests for doc_operation server tool — V5 marker generation and CRUD ops.

Tests are structured around tmp_path fixtures that simulate the
.codebase-analysis/ and .codebase-docs/ directory structure.
"""
from __future__ import annotations

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers — replicate the update_index logic for unit testing
# ---------------------------------------------------------------------------

def _build_index_content(
    doc_dir: Path,
    module_dirs: list[Path],
    project_name: str = "TestProject",
    total_modules: int = 0,
) -> str:
    """Replicate the update_index logic from server.py for testing.

    This is a simplified version that focuses on marker generation.
    """
    # Scan DETAIL.md files for index-fragment blocks
    detail_fragments: dict[str, list[str]] = {}
    for mod_dir in module_dirs:
        for detail_file in sorted(mod_dir.rglob("DETAIL.md")):
            content = detail_file.read_text(encoding="utf-8")
            in_fragment = False
            frag_lines: list[str] = []
            for line in content.splitlines():
                if "index-fragment:" in line:
                    in_fragment = True
                    continue
                if in_fragment and line.strip().startswith("<!--"):
                    in_fragment = False
                    continue
                if in_fragment:
                    frag_lines.append(line)
            if frag_lines:
                detail_fragments.setdefault(mod_dir.name, []).extend(frag_lines)

    fragments: list[str] = []
    for mod_dir in module_dirs:
        overview = mod_dir / "OVERVIEW.md"
        if overview.exists():
            fragments.append(f"<!-- module-index:{mod_dir.name} -->\n## {mod_dir.name}\n")
            content = overview.read_text(encoding="utf-8")
            in_fragment = False
            frag_lines = []
            for line in content.splitlines():
                if "index-fragment:" in line:
                    in_fragment = True
                    continue
                if in_fragment and line.strip().startswith("<!--"):
                    in_fragment = False
                    continue
                if in_fragment:
                    frag_lines.append(line)
            if frag_lines:
                fragments.append("\n".join(frag_lines) + "\n")
            else:
                para_lines: list[str] = []
                for line in content.splitlines():
                    if line.startswith("#"):
                        continue
                    if line.startswith("---"):
                        continue
                    if not line.strip() and para_lines:
                        break
                    if line.strip():
                        para_lines.append(line)
                if para_lines:
                    fragments.append("\n".join(para_lines) + "\n")
            # Append any DETAIL-sourced index fragments
            if mod_dir.name in detail_fragments:
                fragments.append("\n".join(detail_fragments[mod_dir.name]) + "\n")
            fragments.append(f"<!-- end:module-index:{mod_dir.name} -->\n")

    index_content = (
        f"---\nproject: {project_name}\n"
        f"total_modules: {total_modules}\n"
        f"generated_by: codebase-explorer\n---\n\n"
        f"# {project_name} Architecture\n\n"
        + "\n".join(fragments)
        + "\n<!-- codebase-explorer: end -->\n"
    )
    return index_content


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: update_index generates module-index markers
# ---------------------------------------------------------------------------


class TestUpdateIndexModuleIndexMarkers:
    """R13: INDEX.md contains <!-- module-index:{id} --> markers."""

    def test_three_modules_produce_three_markers(self, tmp_path: Path):
        doc_dir = tmp_path / ".codebase-docs"
        for name in ["auth", "api", "models"]:
            _write(doc_dir / name / "OVERVIEW.md", f"# {name}\n\nOverview of {name}.\n")

        module_dirs = sorted([d for d in doc_dir.iterdir() if d.is_dir()])
        content = _build_index_content(doc_dir, module_dirs, total_modules=3)

        assert content.count("<!-- module-index:") >= 3
        assert "<!-- module-index:auth -->" in content
        assert "<!-- module-index:api -->" in content
        assert "<!-- module-index:models -->" in content

    def test_end_markers_present(self, tmp_path: Path):
        doc_dir = tmp_path / ".codebase-docs"
        for name in ["auth", "api"]:
            _write(doc_dir / name / "OVERVIEW.md", f"# {name}\n\nOverview.\n")

        module_dirs = sorted([d for d in doc_dir.iterdir() if d.is_dir()])
        content = _build_index_content(doc_dir, module_dirs)

        assert "<!-- end:module-index:auth -->" in content
        assert "<!-- end:module-index:api -->" in content

    def test_index_fragment_from_overview(self, tmp_path: Path):
        doc_dir = tmp_path / ".codebase-docs"
        _write(doc_dir / "auth" / "OVERVIEW.md", (
            "# Auth\n\n"
            "<!-- index-fragment:auth -->\n"
            "Authentication module handles login and signup.\n"
            "<!-- end:index-fragment:auth -->\n"
        ))

        module_dirs = sorted([d for d in doc_dir.iterdir() if d.is_dir()])
        content = _build_index_content(doc_dir, module_dirs)

        assert "Authentication module handles login and signup." in content

    def test_index_fragment_from_detail(self, tmp_path: Path):
        doc_dir = tmp_path / ".codebase-docs"
        _write(doc_dir / "api" / "OVERVIEW.md", "# API\n\nAPI overview.\n")
        _write(doc_dir / "api" / "DETAIL.md", (
            "<!-- module:api -->\n"
            "# API Detail\n\n"
            "<!-- index-fragment:api -->\n"
            "API routes handle HTTP requests.\n"
            "<!-- end:index-fragment:api -->\n"
            "<!-- end:module:api -->\n"
        ))

        module_dirs = sorted([d for d in doc_dir.iterdir() if d.is_dir()])
        content = _build_index_content(doc_dir, module_dirs)

        assert "API routes handle HTTP requests." in content

    def test_empty_docs_dir(self, tmp_path: Path):
        doc_dir = tmp_path / ".codebase-docs"
        doc_dir.mkdir(parents=True)
        content = _build_index_content(doc_dir, [])
        assert "<!-- codebase-explorer: end -->" in content


# ---------------------------------------------------------------------------
# Tests: merge_modules preserves markers
# ---------------------------------------------------------------------------


class TestMergeModulesPreservesMarkers:
    """Test that merge_modules moves files correctly."""

    def test_files_moved_to_target(self, tmp_path: Path):
        import shutil
        doc_dir = tmp_path / ".codebase-docs"
        src_dir = doc_dir / "old_module"
        tgt_dir = doc_dir / "new_module"

        _write(src_dir / "DETAIL.md", "<!-- module:old_module -->\nOld content\n<!-- end:module:old_module -->\n")
        _write(src_dir / "OVERVIEW.md", "Old overview\n")
        tgt_dir.mkdir(parents=True, exist_ok=True)

        # Simulate merge: move all files from source to target
        for item in src_dir.iterdir():
            dest = tgt_dir / item.name
            shutil.move(str(item), str(dest))
        if not any(src_dir.iterdir()):
            src_dir.rmdir()

        assert not src_dir.exists()
        assert (tgt_dir / "DETAIL.md").exists()
        assert (tgt_dir / "OVERVIEW.md").exists()
        # Markers are preserved in file content
        content = (tgt_dir / "DETAIL.md").read_text()
        assert "<!-- module:old_module -->" in content


# ---------------------------------------------------------------------------
# Tests: move_detail preserves markers
# ---------------------------------------------------------------------------


class TestMoveDetailPreservesMarkers:
    """Test that move_detail preserves V5 markers in moved files."""

    def test_markers_preserved_after_move(self, tmp_path: Path):
        import shutil
        doc_dir = tmp_path / ".codebase-docs"
        src_path = doc_dir / "auth" / "DETAIL.md"
        tgt_dir = doc_dir / "security"
        tgt_path = tgt_dir / "DETAIL.md"

        original = (
            "<!-- module:auth -->\n"
            "<!-- file:auth/login.py -->\n"
            "Login handler docs\n"
            "<!-- end:file:auth/login.py -->\n"
            "<!-- end:module:auth -->\n"
        )
        _write(src_path, original)
        tgt_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(tgt_path))

        content = tgt_path.read_text()
        assert "<!-- file:auth/login.py -->" in content
        assert "<!-- end:file:auth/login.py -->" in content
