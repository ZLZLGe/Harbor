#!/bin/bash
set -euo pipefail

cat > /root/similar_chapter_index.json <<'EOF'
{
  "clip_title": "Floor Plan Tutorial Excerpt A",
  "clip_duration_seconds": 205,
  "chapters": [
    {
      "time": 0,
      "title": "What we'll do"
    },
    {
      "time": 15,
      "title": "How we'll get there"
    },
    {
      "time": 25,
      "title": "Getting a floor plan"
    },
    {
      "time": 92,
      "title": "Getting started"
    },
    {
      "time": 109,
      "title": "Basic Navigation"
    },
    {
      "time": 126,
      "title": "Import your plan into Blender"
    },
    {
      "time": 169,
      "title": "Basic transform operations"
    }
  ]
}
EOF
