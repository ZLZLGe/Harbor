#!/bin/bash
set -euo pipefail

WORKSPACE=${WORKSPACE:-/workspace}
REPO_DIR="${WORKSPACE}/admin-import-service"
PATCH_DIR="${WORKSPACE}/patches"
PATCH_FILE="${PATCH_DIR}/0001-admin-import-type-whitelist.patch"

mkdir -p "${PATCH_DIR}"

cd "${REPO_DIR}"

cat <<'EOF' > src/main/java/com/harbor/adminimport/model/ImportOperation.java
package com.harbor.adminimport.model;

public interface ImportOperation
{
  String kind();
}
EOF

cat <<'EOF' > src/main/java/com/harbor/adminimport/AdminImportHandler.java
package com.harbor.adminimport;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.harbor.adminimport.model.DashboardImport;
import com.harbor.adminimport.model.ImportEnvelope;
import com.harbor.adminimport.model.ImportOperation;
import com.harbor.adminimport.model.ImportResponse;
import com.harbor.adminimport.model.ThemeImport;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class AdminImportHandler implements HttpHandler
{
  private static final String THEME_IMPORT = ThemeImport.class.getName();
  private static final String DASHBOARD_IMPORT = DashboardImport.class.getName();

  private final ObjectMapper mapper = new ObjectMapper();

  @Override
  public void handle(HttpExchange exchange) throws IOException
  {
    if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
      sendJson(exchange, 405, Map.of("error", "method not allowed"));
      return;
    }

    String rawBody = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
    if (rawBody.isBlank()) {
      sendJson(exchange, 400, Map.of("error", "request body is required"));
      return;
    }

    try {
      ImportEnvelope envelope = parseEnvelope(rawBody);
      List<String> importedKinds = envelope.getOperations().stream()
          .map(ImportOperation::kind)
          .toList();

      sendJson(
          exchange,
          200,
          new ImportResponse(envelope.getBatchId(), importedKinds.size(), importedKinds)
      );
    }
    catch (IllegalArgumentException exception) {
      sendJson(exchange, 400, Map.of("error", exception.getMessage()));
    }
    catch (Exception exception) {
      sendJson(exchange, 400, Map.of("error", "invalid import payload"));
    }
  }

  private ImportEnvelope parseEnvelope(String rawBody) throws IOException
  {
    JsonNode root = mapper.readTree(rawBody);
    String batchId = requireText(root, "batchId");
    JsonNode operationsNode = root.get("operations");
    if (operationsNode == null || !operationsNode.isArray() || operationsNode.isEmpty()) {
      throw new IllegalArgumentException("at least one operation is required");
    }

    List<ImportOperation> operations = new ArrayList<>();
    for (JsonNode operationNode : operationsNode) {
      operations.add(parseOperation(operationNode));
    }

    ImportEnvelope envelope = new ImportEnvelope();
    envelope.setBatchId(batchId);
    envelope.setOperations(operations);
    return envelope;
  }

  private ImportOperation parseOperation(JsonNode operationNode) throws IOException
  {
    String requestedClass = requireText(operationNode, "@class");
    if (!operationNode.isObject()) {
      throw new IllegalArgumentException("operation payload must be an object");
    }

    ObjectNode copy = ((ObjectNode) operationNode).deepCopy();
    copy.remove("@class");

    if (THEME_IMPORT.equals(requestedClass)) {
      return mapper.treeToValue(copy, ThemeImport.class);
    }
    if (DASHBOARD_IMPORT.equals(requestedClass)) {
      return mapper.treeToValue(copy, DashboardImport.class);
    }

    throw new IllegalArgumentException("unsupported import type");
  }

  private String requireText(JsonNode node, String fieldName)
  {
    JsonNode value = node.get(fieldName);
    if (value == null || !value.isTextual() || value.asText().isBlank()) {
      throw new IllegalArgumentException(fieldName + " is required");
    }
    return value.asText();
  }

  private void sendJson(HttpExchange exchange, int statusCode, Object payload) throws IOException
  {
    byte[] responseBody = mapper.writeValueAsBytes(payload);
    exchange.getResponseHeaders().set("Content-Type", "application/json");
    exchange.sendResponseHeaders(statusCode, responseBody.length);
    exchange.getResponseBody().write(responseBody);
    exchange.close();
  }
}
EOF

git diff --binary -- src/main/java/com/harbor/adminimport/AdminImportHandler.java src/main/java/com/harbor/adminimport/model/ImportOperation.java > "${PATCH_FILE}"

if [ ! -s "${PATCH_FILE}" ]; then
  echo "failed to generate patch" >&2
  exit 1
fi

mvn -q -DskipTests package dependency:copy-dependencies
