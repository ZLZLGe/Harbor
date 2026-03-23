#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

CLIENT_FILE=/workspace/src/main/java/com/example/customerprofile/client/ProfileGatewayClient.java
LOG_FILE=/logs/verifier/test_output.log

set +e
mvn -q test >/tmp/mvn.log 2>&1
MVN_EXIT=$?
set -e
cat /tmp/mvn.log | tee "$LOG_FILE"

if [ $MVN_EXIT -eq 0 ] \
  && grep -Fq "RestClient" "$CLIENT_FILE" \
  && ! grep -Fq "RestTemplate" "$CLIENT_FILE" \
  && grep -Fq '.uri("/profiles/{customerId}", customerId)' "$CLIENT_FILE" \
  && grep -Fq '.body(CustomerProfile.class)' "$CLIENT_FILE" \
  && grep -Fq '.body(new WelcomeMessageRequest(customerId, templateCode))' "$CLIENT_FILE" \
  && [ "$(grep -Fo '.toBodilessEntity()' "$CLIENT_FILE" | wc -l)" -ge 2 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
