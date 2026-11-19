"""Turn one finished run's map into a narrated short film.

The film is planned by this program, not written by hand and not rewritten by a model: the
overview comes from the tree's root node, the systems from its children, the modules from the
level below, and the function lines from each unit's own detail. Slides are one HTML page
(``data/video_deck.html``) shot by headless Chrome; voice and encode reuse the tools of the
showcase scripts (``showcase/tour/make_audio.py`` for Kokoro speech, then ffmpeg).

Order, straight from the design's reading path: overall purpose, then the systems, then two
modules taken down to their functions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from cbe.catalog_query import read_catalog_text

DEFAULT_SECONDS = 175
DEFAULT_MODULES = 2
FUNCTIONS_PER_MODULE = 4
SECOND_MODULE_FUNCTIONS = 2
FUNCTIONS_FLOOR = 2              # a module that is narrated still shows at least this many functions
WORDS_PER_SECOND = 2.03         # measured on the Kokoro voice at speed 1.06 (397 words, 196 s)
GAP_SAME_SCENE = 0.35           # the gaps make_audio.py inserts
GAP_NEW_SCENE = 0.6
DETAIL_WORDS = 26
FIGURES = ("function", "method", "class")
WIDTH, HEIGHT, FPS = 1920, 1080, 15
MAX_BYTES = 10 * 1024 * 1024

_PAGE_LEAD = re.compile(r"^(?:come here to|start here to|read this page to|this page)\s+", re.IGNORECASE)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


class VideoError(ValueError):
    """The run cannot be turned into a film, or a tool it needs is missing."""


def spoken(text: str) -> str:
    """Plain narration from map prose: no markdown, no page-directed lead-in, one line."""
    text = _MD_LINK.sub(r"\1", text or "")
    text = text.replace("`", "").replace("**", "")
    text = re.sub(r"\s+", " ", text).strip()
    match = _PAGE_LEAD.match(text)
    if match:
        text = text[match.end():]
        if text:
            text = text[0].upper() + text[1:]
    return text


def lead(text: str, words: int) -> str:
    """Whole sentences of ``text``, the first one always, until ``words`` is reached.

    A sentence is never cut in the middle (narration would hear a broken clause); a single
    sentence longer than twice the budget is the only case that gets clipped."""
    text = spoken(text)
    if not text:
        return ""
    out: list[str] = []
    used = 0
    for sentence in _SENTENCE.split(text):
        cost = len(sentence.split())
        if out and used + cost > words:
            break
        out.append(sentence)
        used += cost
    value = " ".join(out)
    if len(value.split()) > 2 * words:
        value = " ".join(value.split()[: 2 * words]).rstrip(",;:") + "."
    return value


def first_sentence(text: str) -> str:
    parts = _SENTENCE.split(spoken(text))
    return parts[0] if parts else ""


def _symbol(uid: str) -> str:
    """The symbol's own name: shared by its overloads and by a function split into ranges."""
    parts = uid.split("::")
    return parts[2] if len(parts) > 2 and parts[2] else uid


class _Map:
    """The tree of one run's catalog, read in page order (the order the catalog stores)."""

    def __init__(self, catalog: dict) -> None:
        self.catalog = catalog
        self.nodes = catalog.get("nodes") or {}
        if not self.nodes:
            raise VideoError("the catalog holds no node tree; regenerate the run with 3.0 or later")
        self.units = catalog.get("units") or {}
        self.children: dict[str, list[str]] = {}
        for nid, node in self.nodes.items():
            parent = node.get("parent")
            if parent in self.nodes:
                self.children.setdefault(parent, []).append(nid)
        roots = [nid for nid in self.nodes if self.nodes[nid].get("parent") not in self.nodes]
        if len(roots) != 1:
            raise VideoError(f"expected one root node, found {len(roots)}: {roots[:4]}")
        self.root = roots[0]
        self.systems = self.children.get(self.root) or [self.root]
        self.name = spoken(self.nodes[self.root].get("title") or "") or self.root
        self._degree = self._call_degree()

    def _call_degree(self) -> dict[str, int]:
        """Resolved call edges per unit; empty when the run has no graph."""
        degree: dict[str, int] = {}
        table = self.catalog.get("edges") or {}
        rows = table.values() if isinstance(table, dict) else table
        for edge in rows:
            if not isinstance(edge, dict) or edge.get("status") != "resolved":
                continue
            for side in ("source_symbol", "target_symbol"):
                uid = edge.get(side)
                if uid in self.units:
                    degree[uid] = degree.get(uid, 0) + 1
        return degree

    def title(self, nid: str) -> str:
        node = self.nodes.get(nid) or {}
        return spoken(node.get("title") or nid)

    def capability(self, nid: str) -> str:
        node = self.nodes.get(nid) or {}
        return spoken(node.get("capability") or "")

    def subtree(self, nid: str) -> list[str]:
        out = [nid]
        for child in self.children.get(nid) or []:
            out += self.subtree(child)
        return out

    def units_of(self, nid: str) -> list[str]:
        out: list[str] = []
        for leaf in self.subtree(nid):
            out += [uid for uid in self.nodes[leaf].get("unit_ids") or [] if uid in self.units]
        return out

    def modules(self) -> list[tuple[str, str, int]]:
        """(system, module, unit count) for the level below the systems."""
        rows = []
        for system in self.systems:
            level = self.children.get(system) or [system]
            for mid in level:
                count = len(self.units_of(mid))
                if count:
                    rows.append((system, mid, count))
        return rows

    def functions(self, nid: str, limit: int) -> list[dict[str, str]]:
        """The most connected units of a module, one per symbol name.

        Overloads and one function split into several ranges share a symbol name; the unit with
        the longest detail speaks for them, because a one-line overload says less than the
        general case."""
        seen: dict[str, dict[str, Any]] = {}
        for position, uid in enumerate(self.units_of(nid)):
            unit = self.units[uid]
            if unit.get("kind") not in FIGURES:
                continue
            detail = lead(unit.get("explain") or unit.get("summary") or "", DETAIL_WORDS)
            if not detail:
                continue
            key = _symbol(uid)
            row = {"name": _symbol(uid), "detail": detail,
                   "degree": self._degree.get(uid, 0), "order": position,
                   "words": len(detail.split())}
            if key not in seen or row["words"] > seen[key]["words"]:
                seen[key] = row
        ranked = sorted(seen.values(), key=lambda row: (-row["degree"], row["order"]))
        return [{"name": row["name"], "detail": row["detail"]} for row in ranked[:limit]]

    def figures(self) -> int:
        return sum(1 for unit in self.units.values() if unit.get("kind") in FIGURES)


def _seconds_of(items: list[dict]) -> float:
    total = 0.0
    previous = None
    for item in items:
        gap = GAP_SAME_SCENE if previous in (None, item["scene"]) else GAP_NEW_SCENE
        total += gap + len(item["say"].split()) / WORDS_PER_SECOND
        previous = item["scene"]
    return total


def _item(number: int, scene: str, say: str, slide: dict) -> dict:
    """One narration line: what is said, which slide state is on screen, how much of it is shown."""
    return {"id": str(number), "scene": scene, "say": say, "caption": say, "slide": slide,
            "reveal": {}}


def build_plan(run_dir: Path, *, modules: int = DEFAULT_MODULES,
               seconds: int = DEFAULT_SECONDS) -> dict[str, Any]:
    """The whole film as data: what is said, what is on the slide, how much of it is shown."""
    catalog = json.loads(read_catalog_text(Path(run_dir)))
    tree_of = _Map(catalog)
    overview = tree_of.nodes[tree_of.root].get("summary") or ""
    if not spoken(overview):
        raise VideoError("the tree's root node has no summary; the run's overview was not written")

    chosen: list[tuple[str, str, int]] = []
    used_systems: set[str] = set()
    for system, mid, count in sorted(tree_of.modules(), key=lambda row: (-row[2], row[1])):
        if len(chosen) >= max(1, modules):
            break
        if system in used_systems and len(used_systems) < len(tree_of.systems):
            continue
        chosen.append((system, mid, count))
        used_systems.add(system)
    if not chosen:
        raise VideoError("no module below the systems owns a unit; nothing to narrate")

    systems = [{"title": tree_of.title(nid), "capability": lead(tree_of.capability(nid), 48)}
               for nid in tree_of.systems]
    plan_modules = []
    for system, mid, count in chosen:
        limit = FUNCTIONS_PER_MODULE if not plan_modules else SECOND_MODULE_FUNCTIONS
        plan_modules.append({
            "id": mid, "system": tree_of.title(system), "title": tree_of.title(mid),
            "capability": lead(tree_of.capability(mid), 60),
            "functions": tree_of.functions(mid, limit), "units": count,
        })

    figures = tree_of.figures()
    stats = {"files": len(catalog.get("files") or {}), "figures": figures,
             "pages": len(tree_of.nodes), "systems": len(tree_of.systems),
             "modules": len(tree_of.modules())}
    plan: dict[str, Any] = {"project": tree_of.name, "stats": stats,
                            "overview": lead(overview, 55), "systems": systems,
                            "modules": plan_modules, "items": []}

    items: list[dict] = []
    counter = 0

    def add(scene: str, say: str, slide: dict, **reveal: Any) -> None:
        nonlocal counter
        counter += 1
        item = _item(counter, scene, say, slide)
        item["reveal"] = dict(reveal)
        items.append(item)

    first = first_sentence(overview)
    add("title", f"{first} {stats['files']} source files, {figures} functions, methods and classes, "
                 f"each with a short explanation of what it does. This map is built from those "
                 f"explanations.",
        {"kind": "title"})
    add("map", f"The map has {len(systems)} parts.", {"kind": "map"}, systems=0)
    for index, system in enumerate(systems, start=1):
        say = f"{system['title']}. {system['capability']}" if system["capability"] else system["title"]
        add("map", say, {"kind": "map"}, systems=index)
    for module in plan_modules:
        slide = {"kind": "module", "module": module["id"]}
        say = f"{module['title']}, inside {module['system']}. {module['capability']}".strip()
        add("module", say, slide, functions=0)
        for index, function in enumerate(module["functions"], start=1):
            add("module", function["detail"], slide, functions=index)
    add("closing", "Every page carries prose only. Signatures, call edges and the source stay one "
                   "command away: cbe find, cbe query, cbe source.",
        {"kind": "closing"})

    _trim(items, plan_modules, seconds)
    _renumber(items)
    plan["modules"] = plan_modules
    plan["items"] = items
    plan["estimated_seconds"] = round(_seconds_of(items), 1)
    return plan


def _trim(items: list[dict], plan_modules: list[dict], seconds: float) -> None:
    """Cut to the target length without leaving a narrated module without functions.

    Function lines go first, but never below ``FUNCTIONS_FLOOR``; then the last module is dropped
    whole, because two lines from two modules beat eight from one."""
    while _seconds_of(items) > seconds:
        roomy = [module for module in plan_modules if len(module["functions"]) > FUNCTIONS_FLOOR]
        if roomy:
            _drop_function(items, max(roomy, key=lambda module: len(module["functions"])))
        elif len(plan_modules) > 1:
            dropped = plan_modules.pop()
            items[:] = [item for item in items if item["slide"].get("module") != dropped["id"]]
        elif len(plan_modules[0]["functions"]) > 1:
            _drop_function(items, plan_modules[0])
        else:
            break


def _drop_function(items: list[dict], module: dict) -> None:
    module["functions"].pop()
    shown = len(module["functions"])
    items[:] = [item for item in items
                if not (item["slide"].get("module") == module["id"]
                        and item["reveal"].get("functions") == shown + 1)]


def _renumber(items: list[dict]) -> None:
    for number, item in enumerate(items, start=1):
        item["id"] = str(number)


def script_document(plan: dict) -> dict:
    """The narration document ``showcase/tour/make_audio.py`` reads."""
    return {"facts": {"symbols": plan["stats"]["figures"]},
            "items": [{"id": item["id"], "scene": item["scene"], "say": item["say"],
                       "caption": item["caption"]} for item in plan["items"]]}


def _showcase_of(showcase: Path | None) -> Path:
    root = Path(__file__).resolve().parents[2]
    path = Path(showcase) if showcase else root / "showcase"
    if not (path / "tour" / "make_audio.py").is_file():
        raise VideoError(f"no showcase scripts under {path}; pass --showcase with the showcase "
                         "directory of the codebase-explorer checkout")
    return path


def _last_line(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[-1] if text else "no output"


def _which(name: str) -> str | None:
    return shutil.which(name) if not Path(name).is_file() else str(Path(name).resolve())


def write_deck(plan: dict, out_dir: Path, showcase: Path) -> Path:
    """The slide page: one HTML file, each slide a state selected by the URL hash."""
    template = (Path(__file__).parent / "data" / "video_deck.html").read_text(encoding="utf-8")
    html = template.replace("__PLAN__", json.dumps(plan, ensure_ascii=False))
    deck = out_dir / "deck.html"
    deck.write_text(html, encoding="utf-8")
    fonts = out_dir / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    for font in sorted((showcase / "fonts").glob("*.woff2")):
        shutil.copyfile(font, fonts / font.name)
    return deck


def render_frames(plan: dict, out_dir: Path, deck: Path, chrome: str) -> list[Path]:
    frames = out_dir / "frames"
    if frames.is_dir():
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    paths = []
    for index, item in enumerate(plan["items"]):
        path = frames / f"{index:03d}-{item['id']}.png"
        result = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--force-device-scale-factor=1", f"--window-size={WIDTH},{HEIGHT}",
             "--virtual-time-budget=1500", f"--screenshot={path}", f"file://{deck}#{index}"],
            capture_output=True, text=True)
        if not path.is_file() or path.stat().st_size == 0:
            raise VideoError(f"Chrome wrote no slide for item {item['id']}: {_last_line(result)}")
        paths.append(path)
    return paths


def synthesize(out_dir: Path, script: Path, showcase: Path, *, python: str | None,
               model: Path | None, voices: Path | None, speed: float) -> dict:
    make_audio = showcase / "tour" / "make_audio.py"
    model = Path(model or os.environ.get("KOKORO_MODEL") or "")
    voices = Path(voices or os.environ.get("KOKORO_VOICES") or "")
    if not model.is_file() or not voices.is_file():
        raise VideoError("set --kokoro-model and --kokoro-voices (or KOKORO_MODEL and "
                         "KOKORO_VOICES) to the Kokoro-82M ONNX model and voices files")
    env = {**os.environ, "KOKORO_MODEL": str(model), "KOKORO_VOICES": str(voices)}
    command = [python or os.environ.get("KOKORO_PYTHON") or "python3", str(make_audio),
               "--script", str(script), "--out", str(out_dir), "--speed", str(speed)]
    result = subprocess.run(command, cwd=str(showcase), capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise VideoError(f"make_audio.py failed ({result.returncode}): {_last_line(result)}")
    return json.loads((out_dir / "timing.json").read_text(encoding="utf-8"))


def captions(plan: dict, timing: dict) -> str:
    """An SRT file next to the film, from the same timeline the slides follow."""
    starts = {row["id"]: (row["t0"], row["t1"]) for row in timing["items"]}
    blocks = []
    for number, item in enumerate(plan["items"], start=1):
        start, end = starts[item["id"]]
        blocks.append(f"{number}\n{_stamp(start)} --> {_stamp(end)}\n{item['caption']}\n")
    return "\n".join(blocks)


def _stamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, milliseconds = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{milliseconds:03d}"


def encode(out_dir: Path, frames: list[Path], timing: dict, ffmpeg: str) -> Path:
    """Stills plus narration to H.264: each slide holds until the next line starts."""
    starts = [row["t0"] for row in timing["items"]]
    total = float(timing["duration"])
    lines = []
    for index, frame in enumerate(frames):
        end = starts[index + 1] if index + 1 < len(starts) else total + GAP_NEW_SCENE
        lines += [f"file '{frame.resolve()}'", f"duration {max(0.05, end - starts[index]):.3f}"]
    lines.append(f"file '{frames[-1].resolve()}'")
    listing = out_dir / "slides.txt"
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")

    video = out_dir / "video.mp4"
    crf = 23

    def run(value: int) -> None:
        command = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                   "-i", str(listing), "-i", str(out_dir / "narration.wav"),
                   "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "slow",
                   "-crf", str(value), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                   "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                   "-c:a", "aac", "-b:a", "96k", "-ac", "1", "-shortest", str(video)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise VideoError(f"ffmpeg failed ({result.returncode}): {_last_line(result)}")

    run(crf)
    while video.stat().st_size > MAX_BYTES and crf < 36:
        crf += 2
        run(crf)
    return video


def make_film(run_dir: Path, out_dir: Path, *, showcase: Path | None = None, modules: int = DEFAULT_MODULES,
              seconds: int = DEFAULT_SECONDS, speed: float = 1.06, chrome: str | None = None,
              ffmpeg: str = "ffmpeg", kokoro_python: str | None = None, model: Path | None = None,
              voices: Path | None = None, plan_only: bool = False) -> dict[str, Any]:
    """Plan, then slides, voice, and encode. Returns the paths and the numbers to report."""
    run_dir = Path(run_dir).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(run_dir, modules=modules, seconds=seconds)
    script = out_dir / "script.json"
    script.write_text(json.dumps(script_document(plan), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    result: dict[str, Any] = {"run_dir": str(run_dir), "out": str(out_dir), "script": str(script),
                              "items": len(plan["items"]), "estimated_seconds": plan["estimated_seconds"],
                              "model_calls": 0}
    if plan_only:
        return result
    showcase_dir = _showcase_of(showcase)
    deck = write_deck(plan, out_dir, showcase_dir)
    chrome_bin = _which(chrome or os.environ.get("CHROME") or "google-chrome") \
        or _which("chromium") or _which("chromium-browser")
    if not chrome_bin:
        raise VideoError("no Chrome found; pass --chrome with the browser the showcase recorder uses")
    frames = render_frames(plan, out_dir, deck, chrome_bin)
    timing = synthesize(out_dir, script, showcase_dir, python=kokoro_python, model=model,
                        voices=voices, speed=speed)
    (out_dir / "captions.srt").write_text(captions(plan, timing), encoding="utf-8")
    video = encode(out_dir, frames, timing, ffmpeg)
    result.update({"deck": str(deck), "video": str(video), "seconds": timing["duration"],
                   "bytes": video.stat().st_size, "frames": len(frames)})
    return result
