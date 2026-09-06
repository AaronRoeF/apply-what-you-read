#!/bin/bash
# Transcode oversized attachments to downscaled JPEG proxies for the agent path.
#
# A coding agent's image Read has a size ceiling. HEIC fails outright, but so do large
# JPEG/PNG -- an earlier version of this script only handled HEIC, and agents hitting
# 5-8MB JPEGs had to hand-roll `sips` mid-batch, exactly the failure the script exists to
# prevent. Scope is therefore "anything large", not "anything HEIC".
#
# Proxies are for READING ONLY. Every downstream record still carries the real vault path.
set -euo pipefail
ATTACH="${1:?usage: make_proxies.sh <attachment-dir> <proxy-dir> [max-bytes]}"
PROXY="${2:?}"
MAX="${3:-2000000}"          # anything over ~2MB gets a proxy regardless of format
mkdir -p "$PROXY"
made=0; skipped=0; failed=0
while IFS= read -r -d '' f; do
  # NB: no ${var,,} -- that is a bashism and this may run under zsh. Use tr.
  lext=$(printf '%s' "${f##*.}" | tr 'A-Z' 'a-z')
  case "$lext" in mov|wav|m4a|zip|json|txt|eml|svg|pot|pptx|xlsx|xlsm|docx|epub|pdf) continue;; esac
  sz=$(stat -f%z "$f")
  # HEIC always needs one; other formats only when oversized
  if [ "$lext" != "heic" ] && [ "$lext" != "heif" ] && [ "$sz" -le "$MAX" ]; then continue; fi
  out="$PROXY/$(basename "${f%.*}").jpg"
  if [ -f "$out" ]; then skipped=$((skipped+1)); continue; fi
  if sips -s format jpeg -s formatOptions 60 -Z 1400 "$f" --out "$out" >/dev/null 2>&1; then
    made=$((made+1))
  else
    failed=$((failed+1)); echo "  FAILED: $(basename "$f")" >&2
  fi
done < <(find "$ATTACH" -type f -print0)
echo "  new proxies: $made   already present: $skipped   failed: $failed"
ls "$PROXY" | wc -l | xargs echo "  total proxies:"
du -sh "$PROXY" | awk '{print "  proxy dir: "$1}'
