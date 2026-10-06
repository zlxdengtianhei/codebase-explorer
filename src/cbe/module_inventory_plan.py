"""Build a structural module candidate from one frozen inventory.

Only source paths and canonical symbol identities determine this tree. Existing
groups, detail prose, and review state in the ledger are deliberately ignored.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any

from cbe.weighting import _is_test_identity


DEFAULT_GROUP_LIMIT = 312
DEFAULT_MAX_SYMBOLS_PER_MODULE = 150
SUPPORT_ROOTS = {
    "t": "test",
    "tests": "test",
    "examples": "example",
    "docs": "docs",
    "extra": "extra",
    "release": "release",
}
SUPPORT_CATALOGUES = {
    "test": ("test-support-catalogue", "Test support catalogue"),
    "example": ("example-support-catalogue", "Example source catalogue"),
    "docs": ("docs-support-catalogue", "Documentation source catalogue"),
    "extra": ("extra-support-catalogue", "Extra source catalogue"),
    "release": ("release-support-catalogue", "Release source catalogue"),
}


@dataclass(frozen=True)
class _Bucket:
    directory: str
    member_ids: tuple[str, ...]
    source_files: tuple[str, ...]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _source_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError(f"{label} must be a relative POSIX source path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or path.as_posix() != value
        or any(part == ".." for part in path.parts)
    ):
        raise ValueError(f"{label} must be a normalized relative POSIX source path")
    return value


def _inventory(ledger: Mapping[str, Any]) -> tuple[str, dict[str, tuple[str, str]]]:
    inventory = _mapping(ledger.get("inventory"), "ledger.inventory")
    revision = ledger.get("source_revision")
    if not isinstance(revision, str) or not revision or inventory.get("source_revision") != revision:
        raise ValueError("source_revision must be nonempty and match the frozen inventory")

    files = _mapping(inventory.get("files"), "ledger.inventory.files")
    for raw_path, raw_record in files.items():
        path = _source_path(raw_path, "inventory file path")
        record = _mapping(raw_record, f"inventory file {path}")
        if record.get("path") != path:
            raise ValueError(f"inventory source file identity disagrees with its path: {path}")

    symbols = _mapping(inventory.get("symbols"), "ledger.inventory.symbols")
    identities: dict[str, tuple[str, str]] = {}
    for symbol_id, raw_record in symbols.items():
        if not isinstance(symbol_id, str) or not symbol_id:
            raise ValueError("canonical symbol IDs must be nonempty strings")
        record = _mapping(raw_record, f"symbol {symbol_id}")
        if record.get("id") != symbol_id:
            raise ValueError(f"canonical symbol ID disagrees with its record: {symbol_id}")
        path = _source_path(record.get("path"), f"symbol {symbol_id} path")
        if path not in files:
            raise ValueError(f"canonical symbol {symbol_id} has no frozen source file: {path}")
        name = record.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"canonical symbol {symbol_id} has an invalid name")
        identities[symbol_id] = path, name
    return revision, identities


def _group_limit(ledger: Mapping[str, Any], requested: int | None) -> int:
    if requested is None:
        policy = ledger.get("documentation_policy")
        if policy is not None:
            policy = _mapping(policy, "documentation_policy")
        requested = (policy or {}).get("group_limit", DEFAULT_GROUP_LIMIT)
    if type(requested) is not int or requested < 1:
        raise ValueError("group_limit must be a positive integer")
    return requested


def _top_level(directory: str) -> str:
    return directory.split("/", 1)[0] if directory != "." else "."


def _common_directory(left: str, right: str) -> str:
    shared: list[str] = []
    for one, two in zip(left.split("/"), right.split("/")):
        if one != two:
            break
        shared.append(one)
    return "/".join(shared) or "."


def _split_directory(
    directory: str,
    member_ids: list[str],
    identities: Mapping[str, tuple[str, str]],
    max_symbols: int,
) -> list[_Bucket]:
    """Keep files whole where possible; split only files larger than the bound."""
    by_file: dict[str, list[str]] = {}
    for symbol_id in member_ids:
        by_file.setdefault(identities[symbol_id][0], []).append(symbol_id)
    if len(member_ids) <= max_symbols:
        return [_Bucket(directory, tuple(sorted(member_ids)), tuple(sorted(by_file)))]

    units: list[tuple[str, tuple[str, ...]]] = []
    for path, ids in sorted(by_file.items()):
        ordered = sorted(ids)
        for start in range(0, len(ordered), max_symbols):
            units.append((path, tuple(ordered[start : start + max_symbols])))
    # Best fit decreasing keeps each file intact unless the file alone is too
    # large. Its sort keys make the result independent of ledger insertion order.
    bins: list[list[tuple[str, tuple[str, ...]]]] = []
    sizes: list[int] = []
    for unit in sorted(units, key=lambda item: (-len(item[1]), item[0], item[1][0])):
        size = len(unit[1])
        fitting = [index for index, used in enumerate(sizes) if used + size <= max_symbols]
        if fitting:
            index = min(fitting, key=lambda item: (max_symbols - sizes[item] - size, item))
            bins[index].append(unit)
            sizes[index] += size
        else:
            bins.append([unit])
            sizes.append(size)
    return sorted(
        (
            _Bucket(
                directory,
                tuple(sorted(sid for _, ids in contents for sid in ids)),
                tuple(sorted({path for path, _ in contents})),
            )
            for contents in bins
        ),
        key=lambda bucket: (bucket.source_files, bucket.member_ids),
    )


def _compact_buckets(
    areas: dict[str, list[_Bucket]],
    identities: Mapping[str, tuple[str, str]],
    limit: int,
    fixed_count: int,
    max_symbols: int,
) -> int:
    """Merge the smallest compatible local buckets without exceeding the bound."""
    count = fixed_count + sum(len(buckets) for buckets in areas.values())
    repacked_areas = 0
    while count > limit:
        choices: list[tuple[tuple[Any, ...], str, int, int]] = []
        for area, buckets in areas.items():
            for left_index, left in enumerate(buckets):
                for right_index in range(left_index + 1, len(buckets)):
                    right = buckets[right_index]
                    size = len(left.member_ids) + len(right.member_ids)
                    if size > max_symbols:
                        continue
                    parent = _common_directory(left.directory, right.directory)
                    score = (
                        size,
                        -len(PurePosixPath(parent).parts),
                        area,
                        left.directory,
                        right.directory,
                        left.member_ids[0],
                        right.member_ids[0],
                    )
                    choices.append((score, area, left_index, right_index))
        if not choices:
            # Whole-file buckets may block a feasible cap (three 100-symbol
            # files need two 150-symbol leaves). Only then split across file
            # boundaries, with a stable path/symbol order within one area.
            repackable = []
            for area, buckets in areas.items():
                total = sum(len(bucket.member_ids) for bucket in buckets)
                minimum = (total + max_symbols - 1) // max_symbols
                if len(buckets) > minimum:
                    repackable.append((total, area))
            if not repackable:
                raise ValueError(
                    f"group_limit {limit} cannot fit the source areas while keeping "
                    f"every production leaf at or below {max_symbols} symbols"
                )
            _, area = min(repackable)
            ordered = sorted(
                (sid for bucket in areas[area] for sid in bucket.member_ids),
                key=lambda sid: (identities[sid][0], sid),
            )
            areas[area] = [
                _Bucket(
                    area,
                    tuple(ordered[start : start + max_symbols]),
                    tuple(sorted({identities[sid][0] for sid in ordered[start : start + max_symbols]})),
                )
                for start in range(0, len(ordered), max_symbols)
            ]
            count = fixed_count + sum(len(current) for current in areas.values())
            repacked_areas += 1
            continue
        _, area, left_index, right_index = min(choices)
        buckets = areas[area]
        left, right = buckets[left_index], buckets[right_index]
        merged = _Bucket(
            _common_directory(left.directory, right.directory),
            tuple(sorted((*left.member_ids, *right.member_ids))),
            tuple(sorted(set(left.source_files) | set(right.source_files))),
        )
        buckets.pop(right_index)
        buckets.pop(left_index)
        buckets.append(merged)
        buckets.sort(key=lambda bucket: (bucket.directory, bucket.source_files, bucket.member_ids))
        count -= 1
    return repacked_areas


def _support_category(path: str, name: str) -> str | None:
    parts = PurePosixPath(path).parts
    if len(parts) > 1 and parts[0] in SUPPORT_ROOTS:
        return SUPPORT_ROOTS[parts[0]]
    # Reuse the author packet's identity guard so a test-only leaf is never
    # accidentally presented as an authorable implementation module.
    if _is_test_identity(SimpleNamespace(path=path, name=name)):
        lower_parts = [part.lower() for part in parts]
        stem = parts[-1].lower().rsplit(".", 1)[0]
        if any(part in {"examples", "example", "samples", "sample"} for part in lower_parts[:-1]) or (
            stem.startswith("example_") or stem.endswith("_example")
        ):
            return "example"
        return "test"
    return None


def _common_support_path(paths: list[str]) -> str:
    directories = [PurePosixPath(path).parent.as_posix() for path in paths]
    common = directories[0]
    for directory in directories[1:]:
        common = _common_directory(common, directory)
    return common


def _group(
    group_id: str,
    parent_id: str | None,
    children: list[str],
    member_ids: list[str],
    title: str,
    question: str,
    inventory_path: str,
    *,
    navigation: bool = False,
) -> dict[str, Any]:
    extra = {
        "review_state": "candidate",
        "candidate_source": "frozen_inventory",
        "inventory_path": inventory_path,
    }
    if navigation:
        extra["presentation"] = "navigation"
    return {
        "group_id": group_id,
        "parent_id": parent_id,
        "children": children,
        "member_ids": member_ids,
        "title": title,
        "question_answered": question,
        "body": "",
        "extra": extra,
    }


def build_inventory_module_plan(
    ledger: dict,
    group_limit: int | None = None,
    max_symbols_per_module: int = DEFAULT_MAX_SYMBOLS_PER_MODULE,
) -> dict:
    """Return an unreviewed, bounded module tree using frozen paths alone.

    Initial production modules follow exact source directories. Oversized
    directories split by whole source files (or bounded chunks of one file).
    When the group cap requires fewer modules, only compatible buckets in the
    same top-level area merge. Support symbols occupy separate catalogues.
    """
    source = _mapping(ledger, "ledger")
    revision, identities = _inventory(source)
    limit = _group_limit(source, group_limit)
    if type(max_symbols_per_module) is not int or max_symbols_per_module < 1:
        raise ValueError("max_symbols_per_module must be a positive integer")

    raw_areas: dict[str, dict[str, list[str]]] = {}
    support: dict[str, list[str]] = {}
    for symbol_id, (path, name) in sorted(identities.items()):
        category = _support_category(path, name)
        if category is not None:
            support.setdefault(category, []).append(symbol_id)
            continue
        directory = PurePosixPath(path).parent.as_posix()
        raw_areas.setdefault(_top_level(directory), {}).setdefault(directory, []).append(symbol_id)

    directory_count = sum(len(buckets) for buckets in raw_areas.values())
    split_directory_count = sum(
        len(ids) > max_symbols_per_module
        for buckets in raw_areas.values() for ids in buckets.values()
    )
    areas = {
        area: sorted(
            (
                bucket for directory, ids in buckets.items()
                for bucket in _split_directory(directory, ids, identities, max_symbols_per_module)
            ),
            key=lambda bucket: (bucket.directory, bucket.source_files, bucket.member_ids),
        )
        for area, buckets in raw_areas.items()
    }
    initial_module_count = sum(len(buckets) for buckets in areas.values())
    fixed_count = 1 + len(areas) + (1 + len(support) if support else 0)
    minimum = fixed_count + sum(
        (sum(len(ids) for ids in buckets.values()) + max_symbols_per_module - 1)
        // max_symbols_per_module
        for buckets in raw_areas.values()
    )
    if minimum > limit:
        raise ValueError(
            f"group_limit {limit} is below minimum {minimum} for "
            f"{len(areas)} top-level source areas, {len(support)} support catalogues, "
            f"and {max_symbols_per_module} symbols per production module"
        )
    repacked_area_count = _compact_buckets(
        areas, identities, limit, fixed_count, max_symbols_per_module
    )

    area_ids = [f"area:{area}" for area in sorted(areas)]
    root_children = area_ids + (["support-catalogue-area"] if support else [])
    groups = {
        "root": _group(
            "root", None, root_children, [], "Source inventory",
            "Where are the catalogued source directories?", ".", navigation=True,
        )
    }
    for area in sorted(areas):
        area_id = f"area:{area}"
        buckets = areas[area]
        by_directory: dict[str, list[_Bucket]] = {}
        for bucket in buckets:
            by_directory.setdefault(bucket.directory, []).append(bucket)
        module_records: list[tuple[str, _Bucket, str]] = []
        for directory, parts in sorted(by_directory.items()):
            for ordinal, bucket in enumerate(parts, 1):
                if len(parts) == 1:
                    module_id = f"module:{directory}"
                    title = f"Source directory {directory}"
                else:
                    module_id = f"module-part:{directory}:{ordinal}"
                    label = bucket.source_files[0] if len(bucket.source_files) == 1 else directory
                    title = f"Source path {label} (part {ordinal} of {len(parts)})"
                module_records.append((module_id, bucket, title))
        module_ids = [module_id for module_id, _, _ in module_records]
        groups[area_id] = _group(
            area_id, "root", module_ids, [], f"Source area {area}",
            f"Which source directories are catalogued under {area}?", area,
            navigation=True,
        )
        for module_id, bucket, title in module_records:
            groups[module_id] = _group(
                module_id, area_id, [], list(bucket.member_ids), title,
                f"Which frozen symbols are catalogued in {title.lower()}?",
                bucket.directory,
            )

    if support:
        categories = [category for category in SUPPORT_CATALOGUES if category in support]
        support_ids = [SUPPORT_CATALOGUES[category][0] for category in categories]
        support_paths = [identities[sid][0] for members in support.values() for sid in members]
        groups["support-catalogue-area"] = _group(
            "support-catalogue-area", "root", support_ids, [],
            "Support source area", "Where are the catalogued support sources?",
            _common_support_path(support_paths), navigation=True,
        )
        for category in categories:
            group_id, title = SUPPORT_CATALOGUES[category]
            members = sorted(support[category])
            groups[group_id] = _group(
                group_id, "support-catalogue-area", [], members, title,
                f"Which frozen {category} symbols are catalogued?",
                _common_support_path([identities[sid][0] for sid in members]),
            )

    production_module_count = sum(len(buckets) for buckets in areas.values())
    module_count = production_module_count + len(support)
    return {
        "source_revision": revision,
        "groups": groups,
        "stats": {
            "group_count": len(groups),
            "module_count": module_count,
            "symbol_count": len(identities),
            "test_symbol_count": len(support.get("test", [])),
            "support_symbol_counts": {
                category: len(support.get(category, [])) for category in SUPPORT_CATALOGUES
            },
            "directory_count": directory_count,
            "split_directory_count": split_directory_count,
            "split_module_count": initial_module_count - directory_count,
            "merged_directory_count": initial_module_count - production_module_count,
            "repacked_area_count": repacked_area_count,
            "max_symbols_per_module": max_symbols_per_module,
            "max_production_module_symbols": max(
                (len(bucket.member_ids) for buckets in areas.values() for bucket in buckets),
                default=0,
            ),
            "group_limit": limit,
        },
    }
