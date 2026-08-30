#!/usr/bin/env bash
# Pin-locked fixture repos (same SHAs as the submodule gitlinks; convenience for
# environments that skip `git submodule update`). Usage: bash test_repos_fetch.sh
set -euo pipefail
cd "$(dirname "$0")/test_repos"
fetch() { local name="$1" url="$2" sha="$3"
  [ -d "$name/.git" ] || git clone --no-checkout "$url" "$name"
  git -C "$name" fetch -q origin "$sha" 2>/dev/null || git -C "$name" fetch -q origin
  git -C "$name" checkout -q "$sha"
  echo "pinned $name @ $sha"
}
fetch flask   https://github.com/pallets/flask.git     4cae5d8e411b1e69949d8fae669afeacbd3e5908
fetch rich    https://github.com/Textualize/rich.git   fc41075a3206d2a5fd846c6f41c4d2becab814fa
fetch celery  https://github.com/celery/celery.git     c35b1d5e3ab04bed018d72e736a862a8bc23ff3f
fetch scrapy  https://github.com/scrapy/scrapy.git     2ce02d417a99343f630d97e6bb8def1760df1366
fetch fastapi https://github.com/fastapi/fastapi.git   937d3075f9456dfcdfe2e1f6bc3b8b7b9a6c6cad
