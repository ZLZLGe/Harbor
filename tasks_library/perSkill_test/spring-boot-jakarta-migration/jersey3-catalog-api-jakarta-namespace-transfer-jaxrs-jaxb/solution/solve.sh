#!/bin/bash
set -euo pipefail

cd /workspace

find src -name "*.java" -type f -print0 | xargs -0 perl -0pi -e '
    s/import javax\.ws\.rs/import jakarta.ws.rs/g;
    s/import javax\.xml\.bind/import jakarta.xml.bind/g;
    s/import javax\.annotation/import jakarta.annotation/g;
'

mvn test -q
