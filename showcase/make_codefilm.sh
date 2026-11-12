#!/usr/bin/env bash
# Build the narrated Flask source film from catalog ranges and exact source files.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ROOT=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --source-root) SOURCE_ROOT="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
[ -n "$SOURCE_ROOT" ] && [ -n "$OUT" ] || { echo "usage: $0 --source-root FLASK_CHECKOUT --out DIR" >&2; exit 2; }
FFMPEG="${FFMPEG:-ffmpeg}"
KOKORO_PYTHON="${KOKORO_PYTHON:-python3}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
cd "$HERE"
python3 prepare_codefilm.py --catalog ../examples/flask/catalog.json.gz --source-root "$SOURCE_ROOT" \
  --script tour/codefilm.en.json --out data/codefilm.json
"$KOKORO_PYTHON" tour/make_audio.py --script tour/codefilm.en.json --out "$OUT" \
  --timing tour/codefilm.en.timing.json --speed 1.08

# Only one Chrome recorder runs at a time.
LOCK="${TMPDIR:-/tmp}/codebase-explorer-tour-record.lock"
exec 9>"$LOCK"
flock 9
uptime
while :; do
  LOAD="$(cut -d' ' -f1 /proc/loadavg)"
  if python3 -c "import sys; sys.exit(float('$LOAD') > 20)"; then break; fi
  echo "1-minute load $LOAD is above 20; waiting 120s"
  sleep 120
done
FPS=15
FRAMES="$OUT/frames"
rm -rf "$FRAMES"; mkdir -p "$FRAMES"
node codefilm-record.mjs --out "$FRAMES" --fps "$FPS" --caption-out "$OUT/caption_segments.txt"

encode() {
  "$FFMPEG" -y -loglevel error -framerate "$FPS" -i "$FRAMES/frame_%05d.png" -i "$OUT/narration.wav" \
    -c:v libx264 -preset slow -crf "$1" -pix_fmt yuv420p -movflags +faststart \
    -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a aac -b:a 96k -ac 1 -shortest "$OUT/flask-code.mp4"
}
CRF_VALUE="${CRF:-24}"
encode "$CRF_VALUE"
while [ "$(stat -c %s "$OUT/flask-code.mp4")" -gt 10485760 ] && [ "$CRF_VALUE" -lt 36 ]; do
  CRF_VALUE=$((CRF_VALUE + 2))
  echo "video exceeds 10 MiB; retrying at CRF $CRF_VALUE"
  encode "$CRF_VALUE"
done
ls -lh "$OUT/flask-code.mp4" "$OUT/narration.wav" "$OUT/timing.json"
