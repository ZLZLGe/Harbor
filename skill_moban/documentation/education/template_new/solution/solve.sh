#!/bin/bash
set -euo pipefail

mkdir -p /app/output
cp /solution/student_lesson.ipynb /app/output/student_lesson.ipynb
cp /solution/instructor_guide.md /app/output/instructor_guide.md
cp /solution/lesson_manifest.json /app/output/lesson_manifest.json
cp /solution/source_map.json /app/output/source_map.json
python /app/workspace/build_lesson_package.py
