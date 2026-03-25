#!/bin/bash
set -euo pipefail

cd /workspace

find src -name "*.java" -type f -print0 | xargs -0 perl -0pi -e '
  s/import javax\.persistence\./import jakarta.persistence./g;
  s/import javax\.validation\./import jakarta.validation./g;
  s/import javax\.servlet\./import jakarta.servlet./g;
'

mvn test
