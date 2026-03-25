package com.harbor.adminimport;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.harbor.adminimport.model.DashboardImport;
import com.harbor.adminimport.model.ImportEnvelope;
import com.harbor.adminimport.model.ImportOperation;
import com.harbor.adminimport.model.ImportResponse;
import com.harbor.adminimport.model.ThemeImport;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

public class AdminImportHandler implements HttpHandler
{
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
      ImportEnvelope envelope = mapper.readValue(rawBody, ImportEnvelope.class);
      validateSupportedOperations(envelope);

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

  private void validateSupportedOperations(ImportEnvelope envelope)
  {
    if (envelope.getBatchId() == null || envelope.getBatchId().isBlank()) {
      throw new IllegalArgumentException("batchId is required");
    }
    if (envelope.getOperations() == null || envelope.getOperations().isEmpty()) {
      throw new IllegalArgumentException("at least one operation is required");
    }

    for (ImportOperation operation : envelope.getOperations()) {
      if (!(operation instanceof ThemeImport) && !(operation instanceof DashboardImport)) {
        throw new IllegalArgumentException("unsupported import type");
      }
    }
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
