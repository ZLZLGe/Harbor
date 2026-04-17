#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

for path in /root/similar_founder_notes.mp3 /root/similar_founder_notes_manifest.json; do
  if [ -f "$path" ]; then
    cp "$path" /logs/verifier/
  fi
done

exit 0
