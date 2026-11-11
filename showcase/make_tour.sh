#!/usr/bin/env bash
# Build a narrated walkthrough from an existing showcase data file.
# Required environment: KOKORO_PYTHON, KOKORO_MODEL, KOKORO_VOICES. FFMPEG and CHROME are optional.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DATA=""; LANG="en"; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --data) DATA="$2"; shift 2;;
    --lang) LANG="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
[ -n "$DATA" ] && [ -n "$OUT" ] || { echo "usage: $0 --data SLUG --lang en --out DIR" >&2; exit 2; }
FFMPEG="${FFMPEG:-ffmpeg}"
KOKORO_PYTHON="${KOKORO_PYTHON:-python3}"
SCRIPT="$HERE/tour/$DATA.$LANG.json"
TIMING="$HERE/tour/$DATA.$LANG.timing.json"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

cd "$HERE"
python3 "tour/check_tour.py" --script "$SCRIPT" --data "data/$DATA.json" --catalog "$HERE/../examples/$DATA/catalog.json.gz"
"$KOKORO_PYTHON" "tour/make_audio.py" --script "$SCRIPT" --out "$OUT" --timing "$TIMING"

# Serialise the expensive frame recording across concurrent invocations.
LOCK="${TMPDIR:-/tmp}/codebase-explorer-tour-record.lock"
exec 9>"$LOCK"
flock 9
uptime
while :; do
  LOAD="$(cut -d' ' -f1 /proc/loadavg)"
  if python3 -c "import sys
try:
    load = float('$LOAD')
except ValueError:
    print('could not read 1-minute load; continuing')
    sys.exit(0)
sys.exit(load > 12)"; then break; fi
  echo "1-minute load $LOAD is above 12; waiting 15s"
  sleep 15
done
FPS=15
FRAMES="$OUT/frames_$DATA"
rm -rf "$FRAMES"; mkdir -p "$FRAMES"
node record.mjs --mode tour --data "$DATA" --lang "$LANG" --out "$FRAMES" --fps "$FPS"

encode() {
  "$FFMPEG" -y -loglevel error -framerate "$FPS" -i "$FRAMES/frame_%05d.png" -i "$OUT/narration.wav" \
    -c:v libx264 -preset slow -crf "$1" -pix_fmt yuv420p -movflags +faststart \
    -c:a aac -b:a 96k -ac 1 -shortest "$OUT/walkthrough-$DATA.mp4"
}
CRF_VALUE="${CRF:-23}"
encode "$CRF_VALUE"
while [ "$(stat -c %s "$OUT/walkthrough-$DATA.mp4")" -gt 8388608 ] && [ "$CRF_VALUE" -lt 35 ]; do
  CRF_VALUE=$((CRF_VALUE + 2))
  echo "video exceeds 8 MB; retrying at CRF $CRF_VALUE"
  encode "$CRF_VALUE"
done
ls -lh "$OUT/walkthrough-$DATA.mp4" "$OUT/narration.wav" "$OUT/timing.json"
