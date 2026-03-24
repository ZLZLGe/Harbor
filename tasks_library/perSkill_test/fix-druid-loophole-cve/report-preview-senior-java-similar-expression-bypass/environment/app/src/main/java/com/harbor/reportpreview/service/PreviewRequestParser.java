package com.harbor.reportpreview.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.harbor.reportpreview.exception.BadPreviewRequestException;
import com.harbor.reportpreview.model.PreviewOptions;
import com.harbor.reportpreview.model.PreviewRequest;
import java.io.IOException;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class PreviewRequestParser
{
  private static final Set<String> KNOWN_FIELDS = Set.of("template", "variables", "options");

  private final ObjectMapper objectMapper;

  public PreviewRequestParser(ObjectMapper objectMapper)
  {
    this.objectMapper = objectMapper;
  }

  public PreviewRequest parse(String rawJson)
  {
    try {
      JsonNode root = objectMapper.readTree(rawJson);
      String template = readRequiredText(root, "template");
      Map<String, String> variables = readVariables(root.path("variables"));
      PreviewOptions options = readOptions(root.path("options"));
      applyLegacyCompatibilityFlags(root, options);
      return new PreviewRequest(template, variables, options);
    }
    catch (IOException exception) {
      throw new BadPreviewRequestException("Preview request is not valid JSON", exception);
    }
  }

  private String readRequiredText(JsonNode root, String fieldName)
  {
    JsonNode node = root.get(fieldName);
    if (node == null || !node.isTextual() || node.asText().isBlank()) {
      throw new BadPreviewRequestException("Missing text field: " + fieldName);
    }
    return node.asText();
  }

  private Map<String, String> readVariables(JsonNode variablesNode) throws IOException
  {
    if (variablesNode.isMissingNode() || variablesNode.isNull()) {
      return Collections.emptyMap();
    }
    if (!variablesNode.isObject()) {
      throw new BadPreviewRequestException("Field 'variables' must be a JSON object");
    }
    return objectMapper.convertValue(variablesNode, new TypeReference<Map<String, String>>() {});
  }

  private PreviewOptions readOptions(JsonNode optionsNode)
  {
    PreviewOptions options = new PreviewOptions();
    if (optionsNode.isMissingNode() || optionsNode.isNull()) {
      return options;
    }
    if (!optionsNode.isObject()) {
      throw new BadPreviewRequestException("Field 'options' must be a JSON object");
    }

    JsonNode localeNode = optionsNode.get("locale");
    if (localeNode != null && localeNode.isTextual() && !localeNode.asText().isBlank()) {
      options.setLocale(localeNode.asText());
    }

    JsonNode trimOutputNode = optionsNode.get("trimOutput");
    if (trimOutputNode != null && trimOutputNode.isBoolean()) {
      options.setTrimOutput(trimOutputNode.asBoolean());
    }

    return options;
  }

  private void applyLegacyCompatibilityFlags(JsonNode root, PreviewOptions options)
  {
    Iterator<Map.Entry<String, JsonNode>> fields = root.fields();
    while (fields.hasNext()) {
      Map.Entry<String, JsonNode> field = fields.next();
      if (KNOWN_FIELDS.contains(field.getKey())) {
        continue;
      }

      JsonNode candidate = field.getValue();
      if (!candidate.isObject()) {
        continue;
      }

      if (candidate.path("allowExpressions").asBoolean(false)) {
        options.setAllowExpressions(true);
      }

      JsonNode previewNode = candidate.path("preview");
      if (previewNode.isObject() && previewNode.path("allowExpressions").asBoolean(false)) {
        options.setAllowExpressions(true);
      }
    }
  }
}
