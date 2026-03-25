package com.harbor.adminimport;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;

public final class AdminImportApplication
{
  private AdminImportApplication()
  {
  }

  public static void main(String[] args) throws IOException, InterruptedException
  {
    int port = Integer.parseInt(System.getenv().getOrDefault("ADMIN_IMPORT_PORT", "18081"));

    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
    server.createContext("/admin/imports", new AdminImportHandler());
    server.setExecutor(Executors.newFixedThreadPool(4));
    server.start();

    System.out.println("admin import service listening on port " + port);
    new CountDownLatch(1).await();
  }
}
