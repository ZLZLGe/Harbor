#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

CONFIG_FILE=/workspace/src/main/java/com/example/compliancearchive/config/ComplianceRestClientConfig.java
CLIENT_FILE=/workspace/src/main/java/com/example/compliancearchive/client/ComplianceArchiveClient.java
LOG_FILE=/logs/verifier/test_output.log

set +e
mvn -q test >/tmp/mvn.log 2>&1
MVN_EXIT=$?
set -e
cat /tmp/mvn.log | tee "$LOG_FILE"

if [ $MVN_EXIT -eq 0 ] \
  && grep -Fq "RestClient" "$CONFIG_FILE" \
  && ! grep -Fq "RestTemplate" "$CONFIG_FILE" \
  && grep -Fq ".baseUrl(baseUrl)" "$CONFIG_FILE" \
  && grep -Fq 'defaultHeader("X-Compliance-Source", "case-ops")' "$CONFIG_FILE" \
  && grep -Fq "RestClient" "$CLIENT_FILE" \
  && ! grep -Fq "RestTemplate" "$CLIENT_FILE" \
  && grep -Fq '.uri("/cases/{caseId}/archive", caseId)' "$CLIENT_FILE" \
  && grep -Fq '.uri("/cases/{caseId}/archive-status", caseId)' "$CLIENT_FILE"; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
