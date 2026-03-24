package com.harbor.pluginmanifest;

import java.nio.file.Path;

public final class ManifestCli {
  private ManifestCli() {
  }

  public static void main(String[] args) {
    if (args.length != 3 || !"import".equals(args[0])) {
      System.err.println("Usage: java -jar plugin-manifest-importer.jar import <manifest.json> <output.json>");
      System.exit(1);
    }

    ManifestImporter importer = new ManifestImporter();
    try {
      importer.importManifest(Path.of(args[1]), Path.of(args[2]));
      System.out.println("Imported manifest into " + args[2]);
    } catch (Exception exception) {
      System.err.println("Import failed: " + exception.getMessage());
      System.exit(1);
    }
  }
}
