#!/usr/bin/env bash
# Append the lesson to a file — for a daily note, an inbox folder, or anything that watches a path.
set -eu
: "${TUTOR_FILE:?TUTOR_FILE is required for the file channel (the path to append to)}"
mkdir -p "$(dirname "$TUTOR_FILE")"
{ printf '\n## %s — %s\n\n' "$(date '+%F %H:%M')" "${2:-lesson}"; cat "$1"; printf '\n'; } >> "$TUTOR_FILE"
echo "tutor: appended to $TUTOR_FILE"
