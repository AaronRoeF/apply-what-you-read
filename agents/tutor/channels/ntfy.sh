#!/usr/bin/env bash
# Push the lesson to a phone through ntfy (https://ntfy.sh or your own server).
#   TUTOR_NTFY_URL=https://ntfy.sh/your-topic  [TUTOR_NTFY_TOKEN=...]
# The title carries the work, because on a phone the title is often all that gets read.
set -eu
: "${TUTOR_NTFY_URL:?TUTOR_NTFY_URL is required for the ntfy channel}"
BODY="$(cat "$1")"
# Most push services truncate hard; the ceiling in the prompt keeps us under it, and the cut is
# marked rather than silent.
if [ "${#BODY}" -gt 3800 ]; then BODY="${BODY:0:3790}
[cut]"; fi
curl -sf -m 15 ${TUTOR_NTFY_TOKEN:+-H "Authorization: Bearer $TUTOR_NTFY_TOKEN"} \
  -H "Title: ${2:-Apply what you read lesson}" -H "Priority: default" -d "$BODY" "$TUTOR_NTFY_URL" >/dev/null
