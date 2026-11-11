#!/usr/bin/env bash
# One command from a CBE catalog to the hero film.
#   ./make_media.sh --catalog RUN/catalog.json --name Flask [--graph GRAPH.json] [--out DIR]
# or, when data/<slug>.json already exists:   ./make_media.sh --slug cjson [--out DIR]
# Outputs in DIR (default ./out): hero_<slug>.mp4, hero_<slug>.gif, hero_<slug>_grid.jpg.
# Environment: FFMPEG (default ffmpeg on PATH), CHROME, CBE_PYTHON (a Python that can run this checkout's `cbe`;
# without it the terminal scene uses a small fallback), CRF, GIF_FPS, GIF_COLORS, GIF_DITHER.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CATALOG=""; NAME=""; GRAPH=""; SLUG=""; OUT="$HERE/out"
while [ $# -gt 0 ]; do
  case "$1" in
    --catalog) CATALOG="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --graph) GRAPH="$2"; shift 2;;
    --slug) SLUG="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown argument: $1" >&2; exit 2;;
  esac
done
FFMPEG="${FFMPEG:-ffmpeg}"
FPS=30
cd "$HERE"
if [ -n "$CATALOG" ]; then
  [ -n "$NAME" ] || { echo "--name is required with --catalog" >&2; exit 2; }
  SLUG="$(printf '%s' "$NAME" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-')"
  python3 prepare_data.py "$CATALOG" --name "$NAME" --out "data/$SLUG.json" ${GRAPH:+--graph "$GRAPH"}
fi
[ -n "$SLUG" ] || { echo "give --catalog and --name, or --slug" >&2; exit 2; }
mkdir -p "$OUT"
FRAMES="$OUT/frames_$SLUG"
rm -rf "$FRAMES"; mkdir -p "$FRAMES"
node record.mjs --data "$SLUG" --out "$FRAMES" --fps "$FPS"
N=$(ls "$FRAMES" | wc -l)
DUR=$(python3 -c "print($N/$FPS)")

# H.264, no audio; faststart for the web
"$FFMPEG" -y -loglevel error -framerate "$FPS" -i "$FRAMES/frame_%05d.png" \
  -c:v libx264 -preset slow -crf "${CRF:-22}" -pix_fmt yuv420p -movflags +faststart -an "$OUT/hero_$SLUG.mp4"

# GIF: 960x540, one optimised palette for the whole film. Over 8 MB? lower GIF_FPS (10), then GIF_COLORS.
"$FFMPEG" -y -loglevel error -framerate "$FPS" -i "$FRAMES/frame_%05d.png" \
  -vf "fps=${GIF_FPS:-12},scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=${GIF_COLORS:-64}:stats_mode=diff[p];[b][p]paletteuse=dither=${GIF_DITHER:-none}:diff_mode=rectangle" \
  -loop 0 "$OUT/hero_$SLUG.gif"

# contact sheet: one settled frame from each of the six scenes (seconds scale with the stage times in app.js)
sel=""
for t in 3.8 10.8 16.8 21.8 26.8 33.3; do
  k=$(python3 -c "print(round($t*$FPS))"); sel="${sel:+$sel+}eq(n\\,$k)"
done
"$FFMPEG" -y -loglevel error -i "$FRAMES/frame_%05d.png" -vf "select='$sel',scale=640:360,tile=3x2" -frames:v 1 -q:v 3 "$OUT/hero_${SLUG}_grid.jpg"
echo "length ${DUR}s"; ls -l "$OUT/hero_$SLUG.mp4" "$OUT/hero_$SLUG.gif" "$OUT/hero_${SLUG}_grid.jpg"
