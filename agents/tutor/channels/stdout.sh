#!/usr/bin/env bash
# The default channel: print the lesson. No account, no key, no network — which is what makes the
# quickstart's promise ("a lesson, from a clean clone, in under half an hour") true for everyone.
set -eu
printf '\n%s\n%s\n\n' "── ${2:-lesson} ──" "$(cat "$1")"
