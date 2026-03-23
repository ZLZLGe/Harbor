#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

CLIENT_FILE=/workspace/src/main/java/com/example/logisticsquotes/client/CarrierQuoteClient.java
LOG_FILE=/logs/verifier/test_output.log

set +e
mvn -q test >/tmp/mvn.log 2>&1
MVN_EXIT=$?
set -e
cat /tmp/mvn.log | tee "$LOG_FILE"

if [ $MVN_EXIT -eq 0 ] \
  && grep -Fq "RestClient" "$CLIENT_FILE" \
  && ! grep -Fq "RestTemplate" "$CLIENT_FILE" \
  && grep -Fq "uri(uriBuilder ->" "$CLIENT_FILE" \
  && grep -Fq "new ParameterizedTypeReference<List<CarrierQuote>>()" "$CLIENT_FILE" \
  && grep -Fq '.uri("/quotes/requests/{quoteRequestId}", quoteRequestId)' "$CLIENT_FILE" \
  && grep -Fq ".toBodilessEntity()" "$CLIENT_FILE"; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
