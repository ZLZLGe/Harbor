#!/bin/bash
set -euo pipefail

cd /workspace
rm -rf build
mkdir -p build/classes

find src/main/java src/test/java -name '*.java' -print0 |           xargs -0 javac --release 21 -d build/classes

java -ea -cp build/classes com.example.clinic.ClinicSmokeCheck
