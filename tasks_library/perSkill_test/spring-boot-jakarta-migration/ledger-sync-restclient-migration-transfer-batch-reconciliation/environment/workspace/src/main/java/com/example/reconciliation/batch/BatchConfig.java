package com.example.reconciliation.batch;

import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class BatchConfig {

    @Bean
    public Job ledgerReconciliationJob(JobRepository jobRepository, Step ledgerReconciliationStep) {
        return new JobBuilder("ledgerReconciliationJob", jobRepository)
            .start(ledgerReconciliationStep)
            .build();
    }

    @Bean
    public Step ledgerReconciliationStep(
        JobRepository jobRepository,
        PlatformTransactionManager transactionManager,
        LedgerReconciliationTasklet ledgerReconciliationTasklet
    ) {
        return new StepBuilder("ledgerReconciliationStep", jobRepository)
            .tasklet(ledgerReconciliationTasklet, transactionManager)
            .build();
    }
}
