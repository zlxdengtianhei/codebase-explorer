#!/usr/bin/env python3
"""Check tour focus IDs and the numeric claims against a prepared catalog."""

import argparse
import collections
import gzip
import json
import re
from pathlib import Path

ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}
WORD = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|and)"


def english_number(phrase):
    words = re.findall(r"[a-z]+", phrase.lower())
    total = 0
    current = 0
    used = False
    for word in words:
        if word == "and":
            continue
        used = True
        if word in ONES:
            current += ONES[word]
        elif word == "hundred":
            current = max(1, current) * 100
        elif word == "thousand":
            total += max(1, current) * 1000
            current = 0
        else:
            return None
    return total + current if used else None


def numbers(text):
    """Return Arabic and English numbers, without interpreting either as text."""
    text = re.sub(r"\beach one\b", "each symbol", text, flags=re.IGNORECASE)
    found = []
    pattern = rf"\b{WORD}(?:[\s-]+{WORD})*\b|\b\d[\d,]*\b"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        token = match.group(0)
        if token[0].isdigit():
            found.append(int(token.replace(",", "")))
        else:
            value = english_number(token)
            if value is not None:
                found.append(value)
    return found


def top_level_ids(data):
    nodes = {node["id"]: node for node in data["nodes"]}
    roots = data.get("roots", [])
    if len(roots) == 1 and nodes[roots[0]].get("children"):
        return set(nodes[roots[0]]["children"])
    return set(roots)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    args = parser.parse_args()
    document = json.loads(args.script.read_text(encoding="utf-8"))
    entries = document["items"]
    data = json.loads(args.data.read_text(encoding="utf-8"))
    with gzip.open(args.catalog, "rt", encoding="utf-8") as stream:
        catalog = json.load(stream)
    errors = []

    kinds = collections.Counter(
        symbol.get("kind") for symbol in catalog["symbols"].values()
        if symbol.get("kind") in {"method", "function", "class"}
    )
    expected_kinds = {"method": 292, "function": 104, "class": 51}
    symbol_count = sum(kinds.values())
    if dict(kinds) != expected_kinds:
        errors.append(f"catalog symbol kinds {dict(kinds)} != {expected_kinds}")
    if document.get("facts", {}).get("symbols") != symbol_count:
        errors.append(f"facts.symbols {document.get('facts', {}).get('symbols')} != catalog {symbol_count}")

    tops = top_level_ids(data)
    nodes = {node["id"] for node in data["nodes"]}
    covered = set()
    for entry in entries:
        focus = entry.get("focus", [])
        if isinstance(focus, str):
            focus = [focus]
        for node_id in focus:
            if node_id not in nodes:
                errors.append(f"{entry['id']}: unknown focus node {node_id}")
            elif node_id not in tops:
                errors.append(f"{entry['id']}: focus is not top-level: {node_id}")
            covered.add(node_id)
    missing = sorted(tops - covered)
    if missing:
        errors.append("top-level nodes not narrated: " + ", ".join(missing))

    expected = {
        "code": {int(data["stats"]["files"]), int(round(data["stats"]["tokens"] / 1000) * 1000)},
        "edges": {symbol_count},
        "modules": {int(data["stats"]["units"])},
    }
    # Scene 4 introduces the system map; the focus scenes reuse its name but have no counts.
    system_intro = next((e for e in entries if e["scene"] == "system" and not e.get("focus")), None)
    if system_intro is None:
        errors.append("missing system introduction")
    else:
        for text in [system_intro["say"], system_intro.get("caption", system_intro["say"])]:
            values = set(numbers(text))
            if values != {len(tops)}:
                errors.append(f"4: module count {sorted(values)} != {len(tops)}")

    for scene, wanted in expected.items():
        scene_entries = [e for e in entries if e["scene"] == scene]
        if not scene_entries:
            errors.append(f"missing scene {scene}")
        for entry in scene_entries:
            for kind in ("say", "caption"):
                values = set(numbers(entry.get(kind, entry["say"])))
                if values != wanted:
                    errors.append(f"{entry['id']} {kind}: numbers {sorted(values)} != {sorted(wanted)}")

    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)
    print(f"OK: {len(tops)} top-level modules covered; counts match "
          f"{data['stats']['files']} files, {symbol_count} symbols "
          f"({kinds['method']} methods + {kinds['function']} functions + {kinds['class']} classes), "
          f"{data['stats']['units']} units, {round(data['stats']['tokens'] / 1000) * 1000:,} tokens")


if __name__ == "__main__":
    main()
