package com.acme.archive.repository;

import com.acme.archive.model.SampleRecord;
import com.acme.archive.model.SampleStatus;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SampleRecordRepository extends JpaRepository<SampleRecord, Long> {

    Optional<SampleRecord> findBySampleCode(String sampleCode);

    List<SampleRecord> findByStatusOrderByArchivedAtAsc(SampleStatus status);
}
