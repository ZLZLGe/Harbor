#!/bin/bash

set -euo pipefail

cd /workspace

cat <<'EOF' > src/main/java/com/acme/archive/model/SampleRecord.java
package com.acme.archive.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.SequenceGenerator;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

@Entity
@Table(name = "sample_record")
public class SampleRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "sample_record_seq")
    @SequenceGenerator(name = "sample_record_seq", sequenceName = "sample_record_seq", allocationSize = 1, initialValue = 1000)
    private Long id;

    @Column(name = "sample_code", nullable = false, unique = true, length = 40)
    private String sampleCode;

    @Enumerated(EnumType.STRING)
    @Column(name = "archive_channel", nullable = false, length = 32)
    private ArchiveChannel archiveChannel;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 24)
    private SampleStatus status;

    @Column(name = "archived_at", nullable = false, columnDefinition = "timestamp with time zone")
    private OffsetDateTime archivedAt;

    @Column(name = "replayed_at", columnDefinition = "timestamp with time zone")
    private OffsetDateTime replayedAt;

    protected SampleRecord() {
    }

    public SampleRecord(
            String sampleCode,
            ArchiveChannel archiveChannel,
            SampleStatus status,
            OffsetDateTime archivedAt,
            OffsetDateTime replayedAt) {
        this.sampleCode = sampleCode;
        this.archiveChannel = archiveChannel;
        this.status = status;
        this.archivedAt = archivedAt;
        this.replayedAt = replayedAt;
    }

    public Long getId() {
        return id;
    }

    public String getSampleCode() {
        return sampleCode;
    }

    public ArchiveChannel getArchiveChannel() {
        return archiveChannel;
    }

    public SampleStatus getStatus() {
        return status;
    }

    public OffsetDateTime getArchivedAt() {
        return archivedAt;
    }

    public OffsetDateTime getReplayedAt() {
        return replayedAt;
    }
}
EOF

cat <<'EOF' > src/test/resources/application.properties
spring.datasource.url=jdbc:h2:mem:archive;MODE=PostgreSQL;DB_CLOSE_DELAY=-1;DATABASE_TO_UPPER=false
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.hibernate.ddl-auto=create
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
spring.sql.init.mode=never
EOF

mvn -q -DskipTests compile
mvn -q test
