#!/usr/bin/env python3
"""Extract one final-video frame per spoken sentence and make a 2-column grid."""

import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cells", type=Path, required=True)
    args = parser.parse_args()
    ffmpeg = os.environ.get("FFMPEG", "ffmpeg")
    timing = json.loads(args.timing.read_text(encoding="utf-8"))
    script = json.loads(args.script.read_text(encoding="utf-8"))
    args.cells.mkdir(parents=True, exist_ok=True)
    cells = []
    for cue, item in zip(timing["items"], script["items"], strict=True):
        parts = [s for s in re.split(r"(?<=[.!?])\s+", item["caption"]) if s]
        total = sum(map(len, parts))
        start = cue["t0"]
        for index, part in enumerate(parts, 1):
            end = cue["t1"] if index == len(parts) else start + (cue["t1"] - cue["t0"]) * len(part) / total
            at = (start + end) / 2
            cell = args.cells / f"{item['id']}.{index}_{at:.3f}.jpg"
            subprocess.run([
                ffmpeg, "-y", "-loglevel", "error", "-ss", f"{at:.6f}", "-i", str(args.video),
                "-frames:v", "1", "-vf", "scale=640:360", "-q:v", "2", str(cell),
            ], check=True)
            cells.append(cell)
            start = end
    grid = Image.new("RGB", (1280, math.ceil(len(cells) / 2) * 360), "#06101b")
    for index, cell in enumerate(cells):
        with Image.open(cell) as image:
            grid.paste(image.convert("RGB"), ((index % 2) * 640, (index // 2) * 360))
    grid.save(args.out, quality=91, subsampling=0)
    print(f"wrote {args.out}: 2 x {len(cells)} cells, {grid.width} x {grid.height}")


if __name__ == "__main__":
    main()
