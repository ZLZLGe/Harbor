package com.harbor.preview;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class PreviewHandler implements HttpHandler
{
  private final ObjectMapper mapper;

  public PreviewHandler(ObjectMapper mapper)
  {
    this.mapper = mapper;
  }

  @Override
  public void handle(HttpExchange exchange) throws IOException
  {
    if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
      writeJson(exchange, 405, Map.of("error", "Method not allowed"));
      return;
    }

    String requestBody = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);

    try {
      PreviewRequest request = mapper.readValue(requestBody, PreviewRequest.class);
      validateAfterDeserialization(request);

      PreviewResponse response = buildPreview(request);
      writeJson(exchange, 200, response);
    }
    catch (IllegalArgumentException e) {
      writeJson(exchange, 400, Map.of("error", e.getMessage()));
    }
    catch (Exception e) {
      writeJson(exchange, 500, Map.of("error", e.getMessage()));
    }
  }

  private void validateAfterDeserialization(PreviewRequest request)
  {
    PreviewRequest.TransformConfig transform = request.getTransform();
    if (transform != null && transform.isScriptMode() && !transform.isScriptEnabled()) {
      throw new IllegalArgumentException("Script preview filters are disabled.");
    }
  }

  private PreviewResponse buildPreview(PreviewRequest request)
  {
    List<Map<String, Object>> rows = request.getSource() == null ? List.of() : request.getSource().getRows();
    PreviewRequest.TransformConfig transform = request.getTransform();

    if (transform != null && transform.isScriptMode()) {
      return new PreviewResponse(true, transform.getExpression(), renderScriptPreview(rows, transform.getField(), transform.getExpression()));
    }

    return new PreviewResponse(false, null, renderFieldPreview(rows, transform == null ? null : transform.getField()));
  }

  private List<Map<String, Object>> renderFieldPreview(List<Map<String, Object>> rows, String field)
  {
    List<Map<String, Object>> previewRows = new ArrayList<>();

    for (Map<String, Object> row : rows) {
      Map<String, Object> rendered = new LinkedHashMap<>();
      if (field == null || field.isBlank()) {
        rendered.putAll(row);
      } else {
        rendered.put(field, row.get(field));
      }
      previewRows.add(rendered);
    }

    return previewRows;
  }

  private List<Map<String, Object>> renderScriptPreview(List<Map<String, Object>> rows, String field, String expression)
  {
    List<Map<String, Object>> previewRows = new ArrayList<>();

    for (Map<String, Object> row : rows) {
      Map<String, Object> rendered = new LinkedHashMap<>();
      Object value = field == null ? row : row.get(field);
      rendered.put("preview", String.valueOf(value) + " :: " + expression);
      previewRows.add(rendered);
    }

    return previewRows;
  }

  private void writeJson(HttpExchange exchange, int statusCode, Object payload) throws IOException
  {
    byte[] body = mapper.writeValueAsBytes(payload);
    exchange.getResponseHeaders().set("Content-Type", "application/json");
    exchange.sendResponseHeaders(statusCode, body.length);
    exchange.getResponseBody().write(body);
    exchange.close();
  }
}
