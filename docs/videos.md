# Walkthrough videos

## Flask's own code, narrated (2 minutes)

One request through Flask: `wsgi_app` pushes the request context, `full_dispatch_request` runs the before-request hooks and the view, `make_response` and `process_response` build the response, and the contexts pop. Then what the application and request contexts hold, how the `current_app` and `request` proxies find them, how blueprints defer registration, and how configuration is loaded. Each sentence, except the two on the `current_app` and `request` proxies, cites a unit explanation in [examples/flask](../examples/flask/docs/INDEX.md) and the Flask source lines it rests on; `globals.py` has no unit explanation in the example, so those two rest on its source alone. The code on screen is that source, with the lines the sentence is about highlighted.

- Watch: https://github.com/user-attachments/assets/87b5b1c1-452e-48e0-af29-2e520391093a
- The voice is synthetic (Kokoro-82M, Apache-2.0). Script: [`showcase/tour/codefilm.en.json`](../showcase/tour/codefilm.en.json); rebuild with [`showcase/make_codefilm.sh`](../showcase/make_codefilm.sh).

## Narrated walkthrough, Flask (2 minutes)

It follows Flask from source files to the module map, visits the eight top-level modules one by one, opens one module page, and shows `cbe find` and `cbe source`. It was recorded from the program-built tree; every number, module name and command output on screen comes from the generated catalog.

- Watch it in the browser, with the transcript in English and Chinese: [narrated walkthrough](https://zlxdengtianhei.github.io/codebase-explorer/film.html)
- File: [walkthrough-flask-1.mp4](https://github.com/zlxdengtianhei/codebase-explorer/releases/download/walkthrough-v2.2.0.dev0/walkthrough-flask-1.mp4)
- The voice is synthetic (Kokoro-82M, Apache-2.0). The script, the recorder and the narration data are in [`showcase/`](../showcase/README.md).

## From the map: a narrated film of any repository (2–3 minutes)

`cbe video` reads one finished run and films that run's own map, in the order the map is meant to be
read: the overall purpose, then every system, then two modules taken down to their functions, and
one closing page for `cbe find`, `cbe query` and `cbe source`. Everything spoken is the map's text:
the overview from the tree's root node, a title plus one capability line per system, a module's
capability, and the detail of up to four functions per module, one line per symbol name (an
overload or a function split into several ranges speaks through its most detailed unit). The
program assembles the script; no model is called, so the same run and the same options give the same
film, and the script step is unit-tested (`tests/test_video_script.py`).

```bash
cbe video --run-dir RUN_DIR --out FILM_DIR [--modules 2] [--seconds 175] [--plan-only]
```

- `RUN_DIR` is a finished run directory holding `catalog.json`. `FILM_DIR` receives `script.json`
  (the narration), `deck.html` (the slides, one state per line), `frames/`, `narration.wav`,
  `timing.json`, `captions.srt` and `video.mp4`.
- Slides are that one HTML page, shot by headless Chrome at 1920×1080; the layout matches the map
  page (`showcase/fonts`, IBM Plex). Voice and encode reuse the showcase tools: Kokoro speech
  through [`showcase/tour/make_audio.py`](../showcase/tour/make_audio.py), then ffmpeg (H.264,
  AAC, loudness normalised). Set `CHROME`, `KOKORO_PYTHON`, `KOKORO_MODEL` and `KOKORO_VOICES` as
  the other films do, or pass `--chrome`, `--kokoro-python`, `--kokoro-model`, `--kokoro-voices`.
  `--showcase` points at another checkout's `showcase/` when `cbe` is installed instead of run here.
- `--seconds` is a target, not a promise: the planner estimates the length from the text
  (2.03 words a second at speed 1.06, measured) and drops later function lines to fit, never
  leaving a narrated module without functions; below that it drops the last module whole.
  `--plan-only` writes `script.json` and stops, which needs neither Chrome nor the voice.
- The text is assembled rather than rewritten by a model because the map's own prose is already
  written for readers, and a rewrite would add a model call, a cost and a run-to-run difference for
  no measured gain.
- Example: the tsdown map in this round (43 files, 138 functions, 3 systems, 51 pages)
  makes the 2:55 film at the top of the README, 3.4 MB, from 14 lines of narration.
