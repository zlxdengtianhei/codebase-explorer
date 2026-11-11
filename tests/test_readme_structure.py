"""The two READMEs (English, Simplified Chinese) must stay in step, and what they link to must exist."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "README.md"
ZH = ROOT / "README.zh-CN.md"
DOCS = sorted((ROOT / "docs").glob("*.md"))

# Paths a README links to that are not in the repository yet, each with the reason. Empty when everything has landed.
PENDING: dict[str, str] = {}

FENCE = re.compile(r"^```.*?^```[ \t]*$", re.S | re.M)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _prose(text: str) -> str:
    return FENCE.sub("", text)


def _commands(text: str) -> set[str]:
    """`cbe ...` and `cbe-install ...` lines from code blocks, and inline code spans that start with them."""
    found = set()
    for block in re.findall(r"^```(?:sh|bash|console)?\n(.*?)^```", text, re.S | re.M):
        for line in re.sub(r"\\\n\s*", " ", block).splitlines():
            line = line.strip()
            if re.match(r"cbe(-install)?( |$)", line):
                found.add(" ".join(line.split()))
    for span in re.findall(r"`([^`\n]+)`", _prose(text)):
        if re.match(r"cbe(-install)?( |$)", span):
            found.add(" ".join(span.split()))
    return found


def _local_targets(text: str) -> set[str]:
    # Links inside code blocks and code spans are quoted text, not links of this page.
    text = re.sub(r"`[^`\n]*`", "", _prose(text))
    targets = set(re.findall(r"\]\(([^)\s]+)\)", text))
    targets |= set(re.findall(r'(?:href|src)="([^"]+)"', text))
    local = set()
    for target in targets:
        if re.match(r"([a-z][a-z0-9+.-]*:|#)", target, re.I):
            continue
        local.add(target.split("#", 1)[0])
    return {t for t in local if t}


def test_both_readmes_exist():
    assert EN.is_file() and ZH.is_file()


def test_first_screen_links_to_the_other_language():
    first_en = "\n".join(_text(EN).splitlines()[:15])
    first_zh = "\n".join(_text(ZH).splitlines()[:15])
    assert "README.zh-CN.md" in first_en
    assert re.search(r'(?:href="|\]\()README\.md', first_zh)


def test_same_number_of_second_level_headings():
    def count(path):
        return len(re.findall(r"^## ", _prose(_text(path)), re.M))

    assert count(EN) == count(ZH) > 0


def test_same_cbe_commands_in_both():
    en, zh = _commands(_text(EN)), _commands(_text(ZH))
    assert en, "no cbe commands found in README.md"
    assert en == zh, {"only_en": sorted(en - zh), "only_zh": sorted(zh - en)}


def test_relative_paths_exist():
    missing = []
    for page in [EN, ZH, *DOCS]:
        for target in _local_targets(_text(page)):
            path = (page.parent / target).resolve()
            rel = path.relative_to(ROOT).as_posix() if ROOT in path.parents or path == ROOT else target
            if not path.exists() and rel not in PENDING:
                missing.append(f"{page.name}: {target}")
    assert not missing, missing


def test_pending_list_gives_a_reason_for_each_entry():
    assert all(reason.strip() for reason in PENDING.values())


def test_no_local_machine_paths():
    for page in [EN, ZH, *DOCS]:
        assert not re.search(r"/hom[e]/|/User[s]/", _text(page)), page.name
