package com.acme.archive.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import org.hibernate.annotations.GenericGenerator;
import org.hibernate.annotations.Parameter;
import org.hibernate.annotations.Type;

@Entity
@Table(name = "sample_record")
public class SampleRecord {

    @Id
    @GeneratedValue(generator = "sample_record_seq")
    @GenericGenerator(
            name = "sample_record_seq",
            strategy = "org.hibernate.id.enhanced.SequenceStyleGenerator",
            parameters = {
                @Parameter(name = "sequence_name", value = "sample_record_seq"),
                @Parameter(name = "increment_size", value = "50")
            })
    private Long id;

    @Column(name = "sample_code", nullable = false, unique = true, length = 40)
    private String sampleCode;

    @Column(name = "archive_channel", nullable = false, length = 32)
    private ArchiveChannel archiveChannel;

    @Enumerated(EnumType.ORDINAL)
    @Column(name = "status", nullable = false, length = 24)
    private SampleStatus status;

    @Type(type = "org.hibernate.type.OffsetDateTimeType")
    @Column(name = "archived_at", nullable = false, columnDefinition = "timestamp with time zone")
    private OffsetDateTime archivedAt;

    @Type(type = "org.hibernate.type.OffsetDateTimeType")
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
