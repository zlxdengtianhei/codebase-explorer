#!/usr/bin/env python3
"""Synthesize a narrated tour and its deterministic virtual-clock timeline."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


def sentence_splits(samples, rate, text):
    """Times (s from the clip start) of the pauses between sentences, or [] when not found.

    Each boundary is the middle of the longest quiet run (at least 0.12 s) within 1.5 s of
    where the sentence lengths put it. Captions use these instead of character shares."""
    parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]
    if len(parts) < 2:
        return []
    frame = max(1, round(rate * 0.01))
    count = len(samples) // frame
    quiet = [float(np.abs(samples[i * frame:(i + 1) * frame]).max()) < 0.005 for i in range(count)]
    runs, i = [], 0
    while i < count:
        if quiet[i]:
            j = i
            while j < count and quiet[j]:
                j += 1
            if j - i >= 12:
                runs.append((i, j))
            i = j
        else:
            i += 1
    total, seen, splits = sum(len(p) for p in parts), 0, []
    for part in parts[:-1]:
        seen += len(part)
        estimate = count * seen / total
        near = [r for r in runs if abs((r[0] + r[1]) / 2 - estimate) <= 150]
        if not near:
            return []
        best = max(near, key=lambda r: (r[1] - r[0], -abs((r[0] + r[1]) / 2 - estimate)))
        splits.append((best[0] + best[1]) / 2 * frame / rate)
    return splits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timing", type=Path, help="also write the timeline here for browser playback")
    parser.add_argument("--model", default=None, type=Path)
    parser.add_argument("--voices", default=None, type=Path)
    parser.add_argument("--speed", default=1.06, type=float)
    args = parser.parse_args()

    import os
    model = args.model or os.environ.get("KOKORO_MODEL")
    voices = args.voices or os.environ.get("KOKORO_VOICES")
    if not model or not voices:
        parser.error("set --model and --voices, or KOKORO_MODEL and KOKORO_VOICES")

    document = json.loads(args.script.read_text(encoding="utf-8"))
    entries = document["items"]
    args.out.mkdir(parents=True, exist_ok=True)
    clips = args.out / "clips"
    clips.mkdir(exist_ok=True)
    voice = None

    audio = []
    timeline = []
    cursor = 0.0
    rate = None
    previous_scene = None
    for entry in entries:
        if previous_scene is not None:
            gap = 0.6 if entry["scene"] != previous_scene else 0.35
            audio.append(np.zeros(round(gap * rate), dtype=np.float32))
            cursor += gap
        clip_path = clips / f"{entry['id']}.wav"
        meta_path = clips / f"{entry['id']}.json"
        cache_key = hashlib.sha256(json.dumps({
            "say": entry["say"], "voice": "am_michael", "speed": args.speed,
            "lang": "en-us", "trim_threshold": 0.002,
        }, sort_keys=True).encode("utf-8")).hexdigest()
        cached = False
        if clip_path.exists() and meta_path.exists():
            try:
                cached = json.loads(meta_path.read_text(encoding="utf-8"))["key"] == cache_key
            except (KeyError, ValueError):
                pass
        if cached:
            samples, sample_rate = sf.read(clip_path, dtype="float32")
        else:
            if voice is None:
                voice = Kokoro(str(model), str(voices))
            samples, sample_rate = voice.create(
                entry["say"], voice="am_michael", speed=args.speed, lang="en-us"
            )
            samples = np.asarray(samples, dtype=np.float32)
            # Kokoro adds a short silent pad to every utterance. Remove only samples below
            # hearing threshold; the requested 0.35/0.6 s gaps are added explicitly below.
            active = np.flatnonzero(np.abs(samples) > 0.002)
            if active.size:
                samples = samples[active[0]:active[-1] + 1]
            sf.write(clip_path, samples, sample_rate, subtype="PCM_16")
            meta_path.write_text(json.dumps({"key": cache_key}) + "\n", encoding="utf-8")
        if rate is not None and sample_rate != rate:
            raise RuntimeError("Kokoro changed its sample rate between clips")
        rate = sample_rate
        samples = np.asarray(samples, dtype=np.float32)
        t0 = cursor
        # ONNX execution can differ by a few samples between identical runs. Quantise
        # upward and pad with silence so the virtual clock is reproducible. The final
        # utterance needs no extra end hold, so it uses the finer 50 ms grid.
        quantum = round(rate * (0.05 if entry is entries[-1] else 0.1))
        padded_length = ((len(samples) + quantum - 1) // quantum) * quantum
        audio.append(samples)
        audio.append(np.zeros(padded_length - len(samples), dtype=np.float32))
        t1 = t0 + padded_length / rate
        cue = {"id": entry["id"], "scene": entry["scene"], "t0": round(t0, 6), "t1": round(t1, 6)}
        splits = sentence_splits(samples, rate, entry["say"])
        if splits:
            cue["splits"] = [round(t0 + split, 3) for split in splits]
        timeline.append(cue)
        print(f"{entry['id']:>2}  {t0:7.3f}–{t1:7.3f}  ({t1 - t0:5.3f}s)")
        cursor = t1
        previous_scene = entry["scene"]

    duration = cursor
    sf.write(args.out / "narration.wav", np.concatenate(audio), rate, subtype="PCM_16")
    result = {"voice": "am_michael", "speed": args.speed, "sample_rate": rate, "duration": round(duration, 6), "items": timeline}
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    (args.out / "timing.json").write_text(encoded, encoding="utf-8")
    if args.timing:
        args.timing.parent.mkdir(parents=True, exist_ok=True)
        args.timing.write_text(encoded, encoding="utf-8")
    print(f"total {duration:.3f}s; wrote {args.out / 'narration.wav'} and timing.json")


if __name__ == "__main__":
    main()
