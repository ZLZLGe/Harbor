package com.harbor.preview;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;

public class PreviewServer
{
  public static void main(String[] args) throws IOException
  {
    int port = Integer.parseInt(System.getenv().getOrDefault("PREVIEW_PORT", "8080"));
    ObjectMapper mapper = new ObjectMapper();

    HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
    server.createContext("/health", exchange -> {
      byte[] body = "{\"status\":\"ok\"}".getBytes(StandardCharsets.UTF_8);
      exchange.getResponseHeaders().set("Content-Type", "application/json");
      exchange.sendResponseHeaders(200, body.length);
      exchange.getResponseBody().write(body);
      exchange.close();
    });
    server.createContext("/api/v1/preview", new PreviewHandler(mapper));
    server.setExecutor(Executors.newFixedThreadPool(4));
    server.start();

    System.out.println("Preview service listening on port " + port);
  }
}
