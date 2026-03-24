package com.example.reporting.client;

public record ArchiveImportConfirmation(
    String exportId,
    String archivePath,
    String checksum,
    String importedAt,
    boolean successful
) {
}
