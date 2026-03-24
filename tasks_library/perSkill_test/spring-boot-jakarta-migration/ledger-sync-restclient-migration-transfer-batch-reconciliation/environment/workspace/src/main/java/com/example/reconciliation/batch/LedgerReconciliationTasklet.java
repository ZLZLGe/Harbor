package com.example.reconciliation.batch;

import com.example.reconciliation.client.LedgerConfirmation;
import com.example.reconciliation.client.LedgerConfirmationBatch;
import com.example.reconciliation.client.LedgerEntry;
import com.example.reconciliation.client.LedgerSyncClient;
import com.example.reconciliation.client.PageEnvelope;
import java.time.LocalDate;
import java.util.List;
import org.springframework.batch.core.StepContribution;
import org.springframework.batch.core.scope.context.ChunkContext;
import org.springframework.batch.core.step.tasklet.Tasklet;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.stereotype.Component;

@Component
public class LedgerReconciliationTasklet implements Tasklet {

    private final LedgerSyncClient ledgerSyncClient;

    public LedgerReconciliationTasklet(LedgerSyncClient ledgerSyncClient) {
        this.ledgerSyncClient = ledgerSyncClient;
    }

    @Override
    public RepeatStatus execute(StepContribution contribution, ChunkContext chunkContext) {
        PageEnvelope<LedgerEntry> page = ledgerSyncClient.fetchEntries(
            null,
            2,
            LocalDate.of(2025, 3, 1)
        );

        List<LedgerConfirmation> confirmations = page.items().stream()
            .map(entry -> new LedgerConfirmation(entry.entryId(), "MATCHED"))
            .toList();

        ledgerSyncClient.submitConfirmations(
            new LedgerConfirmationBatch("run-2025-03-01", confirmations)
        );
        return RepeatStatus.FINISHED;
    }
}
