package com.acme.archive.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.acme.archive.model.ArchiveChannel;
import com.acme.archive.model.SampleRecord;
import com.acme.archive.model.SampleStatus;
import jakarta.persistence.EntityManager;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.jdbc.Sql;

@DataJpaTest
class SampleRecordRepositoryTest {

    @Autowired
    private SampleRecordRepository repository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private EntityManager entityManager;

    @Test
    @Sql(statements = "ALTER SEQUENCE sample_record_seq RESTART WITH 1000")
    void archivesSampleUsingDatabaseSequenceAndReadableEnums() {
        SampleRecord archived = repository.saveAndFlush(new SampleRecord(
                "BIO-2024-0007",
                ArchiveChannel.BIO_BANK,
                SampleStatus.ARCHIVED,
                OffsetDateTime.of(2024, 4, 18, 9, 45, 12, 0, ZoneOffset.ofHours(8)),
                null));

        assertThat(archived.getId()).isEqualTo(1000L);

        String storedChannel = jdbcTemplate.queryForObject(
                "select archive_channel from sample_record where id = ?",
                String.class,
                archived.getId());
        String storedStatus = jdbcTemplate.queryForObject(
                "select status from sample_record where id = ?",
                String.class,
                archived.getId());

        assertThat(storedChannel).isEqualTo("BIO_BANK");
        assertThat(storedStatus).isEqualTo("ARCHIVED");
    }

    @Test
    void replaysHistoryWithoutLosingTimestampInstant() {
        OffsetDateTime archivedAt = OffsetDateTime.of(2024, 3, 3, 6, 30, 0, 0, ZoneOffset.ofHours(-5));
        OffsetDateTime replayedAt = OffsetDateTime.of(2024, 3, 12, 18, 5, 0, 0, ZoneOffset.ofHours(2));
        repository.saveAndFlush(new SampleRecord(
                "HIST-2024-011",
                ArchiveChannel.LONG_TERM_VAULT,
                SampleStatus.REPLAYED,
                archivedAt,
                replayedAt));

        entityManager.clear();

        SampleRecord loaded = repository.findBySampleCode("HIST-2024-011").orElseThrow();
        assertThat(loaded.getArchivedAt().toInstant()).isEqualTo(archivedAt.toInstant());
        assertThat(loaded.getReplayedAt().toInstant()).isEqualTo(replayedAt.toInstant());
    }

    @Test
    void listsReplayHistoryInArchiveOrder() {
        repository.save(new SampleRecord(
                "RUN-01",
                ArchiveChannel.CLINICAL_FREEZER,
                SampleStatus.REPLAYED,
                OffsetDateTime.of(2024, 1, 10, 8, 0, 0, 0, ZoneOffset.UTC),
                OffsetDateTime.of(2024, 1, 12, 8, 0, 0, 0, ZoneOffset.UTC)));
        repository.saveAndFlush(new SampleRecord(
                "RUN-02",
                ArchiveChannel.CLINICAL_FREEZER,
                SampleStatus.REPLAYED,
                OffsetDateTime.of(2024, 1, 11, 8, 0, 0, 0, ZoneOffset.UTC),
                OffsetDateTime.of(2024, 1, 13, 8, 0, 0, 0, ZoneOffset.UTC)));

        entityManager.clear();

        List<SampleRecord> history = repository.findByStatusOrderByArchivedAtAsc(SampleStatus.REPLAYED);
        assertThat(history).extracting(SampleRecord::getSampleCode).containsExactly("RUN-01", "RUN-02");
    }
}
