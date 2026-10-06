"""Deterministic concrete facts: defaults, constants, tables, templates, raises."""

from __future__ import annotations

import importlib
import json

from cbe.concrete_facts import file_facts

generator = importlib.import_module("cbe.generate")

FIXTURE = '''\
DEFAULT_TIMEOUT = 4.0
RETRY_BACKOFF = (0.2, 0.5)
QUEUE_FORMAT = '{hostname}.dq2'
LOG_FORMAT = '[%(levelname)s] %(message)s'
HOSTNAME_FMT = '%n@%h'
OPTIONS = {
    'task': Namespace(
        acks_on_failure_or_timeout=Option(True, type='bool'),
        max_retries=Option(3, type='int'),
    ),
    'worker': Namespace(
        concurrency=Option(4, type='int'),
    ),
}


class Task:
    priority = 10

    def retry(self, countdown=None, max_retries=3):
        if countdown is None:
            raise RetryError('countdown is required')
        return countdown

    async def poll(self, timeout=0.5):
        return timeout


def announce(name, template='Hello %s'):
    banner = '%(name)s joined'
    raise ValueError('unsupported name')
'''


def _by_kind(rows):
    kinds: dict[str, list[dict]] = {}
    for row in rows:
        kinds.setdefault(row["kind"], []).append(row)
    return kinds


def test_all_five_kinds_with_lines_and_kind_priority_order():
    facts = file_facts("demo.py", FIXTURE)
    rows = facts["rows"]
    order = ["param_default", "constant", "option", "template", "raise"]
    positions = [order.index(row["kind"]) for row in rows]
    assert positions == sorted(positions)
    kinds = _by_kind(rows)

    defaults = {row["symbol"]: row for row in kinds["param_default"]}
    assert defaults["retry"]["text"] == "retry(self, countdown=None, max_retries=3)"
    assert defaults["retry"]["line"] == FIXTURE[:FIXTURE.index("    def retry")].count("\n") + 1
    assert defaults["announce"]["text"] == "announce(name, template='Hello %s')"
    assert defaults["poll"]["text"] == "poll(self, timeout=0.5)"

    constants = {row["symbol"]: row for row in kinds["constant"]}
    assert constants["DEFAULT_TIMEOUT"]["text"] == "4.0"
    assert constants["RETRY_BACKOFF"]["text"] == "(0.2, 0.5)"
    assert constants["Task.priority"]["text"] == "10"

    options = {row["symbol"]: row for row in kinds["option"]}
    assert options["OPTIONS.task.acks_on_failure_or_timeout"]["text"] == "Option(True, type='bool')"
    leaf = FIXTURE.index("acks_on_failure_or_timeout=")
    assert options["OPTIONS.task.acks_on_failure_or_timeout"]["line"] == FIXTURE[:leaf].count("\n") + 1
    assert options["OPTIONS.worker.concurrency"]["text"] == "Option(4, type='int')"

    templates = {row["symbol"]: row for row in kinds["template"]}
    assert templates["QUEUE_FORMAT"]["placeholders"] == ["{hostname}"]
    assert templates["LOG_FORMAT"]["placeholders"] == ["%(levelname)s", "%(message)s"]
    assert templates["HOSTNAME_FMT"]["placeholders"] == ["%n", "%h"]
    assert templates["template"]["placeholders"] == ["%s"]  # announce's default
    assert templates["banner"]["placeholders"] == ["%(name)s"]  # announce's local

    raises = kinds["raise"]
    assert [row["text"] for row in raises] == [
        "raise RetryError('countdown is required')", "raise ValueError('unsupported name')"]


def test_facts_split_between_file_and_symbol_buckets():
    facts = file_facts("demo.py", FIXTURE)
    file_symbols = {row["symbol"] for row in facts["file"]}
    assert {"DEFAULT_TIMEOUT", "RETRY_BACKOFF", "QUEUE_FORMAT", "LOG_FORMAT",
            "HOSTNAME_FMT", "OPTIONS.task.acks_on_failure_or_timeout"} <= file_symbols
    assert set(facts["symbols"]) == {"Task", "Task.retry", "Task.poll", "announce"}
    retry = {row["kind"] for row in facts["symbols"]["Task.retry"]}
    assert retry == {"param_default", "raise"}
    assert {row["kind"] for row in facts["symbols"]["Task"]} == {"constant"}


def test_noise_stays_out_rebinding_sets_and_nonliteral_raises():
    source = (
        "LIMIT = 1\n"
        "LIMIT = 2\n"
        "OLD_NAMES = {'celery_{0}'}\n"
        "SMALL = {'a': 1, 'b': 2}\n"
        "BIG = {'k%03d' % 1: 2 for _ in range(40)}\n"
        "def check(flag, code=1):\n"
        "    raise ValueError(code)\n"
        "    raise KeyError\n"
        "    raise TypeError('a %s' % code)\n"
    )
    facts = file_facts("noise.py", source)
    rows = {row["symbol"]: row for row in facts["rows"]}
    assert "LIMIT" not in rows  # rebound at module level
    assert "OLD_NAMES" not in rows  # sets are not tuples, lists or dicts
    assert rows["SMALL"]["kind"] == "constant" and rows["SMALL"]["text"] == "{'a': 1, 'b': 2}"
    assert "BIG" not in rows  # comprehension: not a literal, not a plain table
    assert facts["symbols"]["check"][0]["text"] == "check(flag, code=1)"
    assert not [row for row in facts["symbols"]["check"] if row["kind"] == "raise"]


def test_text_is_capped_at_one_hundred_sixty_chars():
    source = f"LONG_DEFAULT = '{'a' * 200}'\n" + (
        "def wait(timeout='%s'):\n    pass\n")
    facts = file_facts("long.py", source)
    constant = next(row for row in facts["rows"] if row["symbol"] == "LONG_DEFAULT")
    assert len(constant["text"]) == 160 and constant["truncated"] is True
    assert all(len(row["text"]) <= 160 for row in facts["rows"])
    template = next(row for row in facts["rows"] if row["kind"] == "template")
    assert template["symbol"] == "timeout" and template["placeholders"] == ["%s"]


def test_nested_dict_call_and_flat_shapes_follow_structure_not_names():
    source = (
        "TABLE = dict(task=Namespace(acks_late=Option(False), share=Option(True)), "
        "worker=dict(pool=4, max=8))\n"
        "FLATCALL = build(a=1, b=2)\n"
    )
    facts = file_facts("shapes.py", source)
    options = {row["symbol"]: row["text"] for row in facts["rows"] if row["kind"] == "option"}
    assert options == {
        "TABLE.task.acks_late": "Option(False)",
        "TABLE.task.share": "Option(True)",
        "TABLE.worker.pool": "4",
        "TABLE.worker.max": "8",
        "FLATCALL.a": "1",
        "FLATCALL.b": "2",
    }


def _render_repo(tmp_path, source, filler_sentences):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "defaults.py").write_text(source, encoding="utf-8")
    files = generator.scan(repo)
    modules = generator.plan(files)
    for module in modules:
        module.output = {"summary": "Summary sentence. " * filler_sentences,
                         "flow": "Flow sentence. " * filler_sentences,
                         "test_coverage": "Covered. " * filler_sentences,
                         "key_behaviors": [], "uncertainties": []}
    run_dir = tmp_path / "run"
    generator._render(repo, run_dir, files, modules,
                      {"overview": "Demo package.", "maintenance_navigation": "Open the defaults page."})
    return run_dir


def _module_page(run_dir):
    pages = list((run_dir / "docs" / "modules").glob("*.md"))
    assert len(pages) == 1
    return pages[0].read_text(encoding="utf-8")


def test_render_keeps_facts_in_catalog_off_pages_and_points_to_find(tmp_path):
    # A large page: under the old on-page rendering this fixture printed a
    # facts table, so the negative assertions below prove the removal.
    run_dir = _render_repo(tmp_path, FIXTURE, filler_sentences=600)
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    entry = catalog["files"]["pkg/defaults.py"]
    assert any(row["kind"] == "option" and "acks_on_failure_or_timeout" in row["symbol"]
               for row in entry["facts"])
    assert "facts" not in catalog["files"]["pkg/__init__.py"]
    task = catalog["symbols"]["pkg/defaults.py::Task"]
    assert any(row["kind"] == "constant" and row["text"] == "10" for row in task["facts"])
    retry = catalog["symbols"]["pkg/defaults.py::Task.retry"]
    assert {row["kind"] for row in retry["facts"]} == {"param_default", "raise"}
    page = _module_page(run_dir)
    assert "## Constants and defaults (mechanical)" not in page
    assert "acks_on_failure_or_timeout" not in page
    index = (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "cbe find" in index and "cbe query" in index


def test_find_returns_a_fact_by_name_and_query_returns_the_entry(tmp_path):
    run_dir = _render_repo(tmp_path, FIXTURE, filler_sentences=2)
    matches = generator.find(run_dir, "DEFAULT_TIMEOUT")
    assert matches and matches[0]["id"] == "pkg/defaults.py"
    record = generator.query(run_dir, "pkg/defaults.py")
    assert record["id"] == "pkg/defaults.py" and record["facts"]


def test_catalog_keeps_every_fact_when_pages_print_none(tmp_path):
    entries = "\n".join(f"    key_{index:03d}=Option({index}, type='int'),"
                        for index in range(100))
    source = f"TABLE = Namespace(\n{entries}\n)\n"
    run_dir = _render_repo(tmp_path, source, filler_sentences=600)
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["files"]["pkg/defaults.py"]["facts"]) == 100
    page = _module_page(run_dir)
    assert "## Constants and defaults (mechanical)" not in page
    assert "key_099" not in page


def test_extraction_is_deterministic():
    assert file_facts("demo.py", FIXTURE) == file_facts("demo.py", FIXTURE)


def test_unparsable_source_yields_no_facts():
    assert file_facts("broken.py", "def broken(:\n") == {"file": [], "symbols": {}, "rows": []}
