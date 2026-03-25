package com.example.invoice.domain;

import jakarta.persistence.Entity;
import jakarta.persistence.PrePersist;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class InvoiceRecordJpaAnnotationTest {

    @Test
    void shouldExposeJakartaEntityAnnotations() {
        assertThat(InvoiceRecord.class.isAnnotationPresent(Entity.class)).isTrue();

        Method[] methods = InvoiceRecord.class.getDeclaredMethods();
        boolean hasPrePersist = false;
        for (Method method : methods) {
            if (method.isAnnotationPresent(PrePersist.class)) {
                hasPrePersist = true;
                break;
            }
        }

        assertThat(hasPrePersist).isTrue();

        InvoiceRecord record = new InvoiceRecord("INV-1007", "CUSTOMER-9", new BigDecimal("15.30"));
        assertThat(record.getInvoiceNumber()).isEqualTo("INV-1007");
        assertThat(record.getCustomerCode()).isEqualTo("CUSTOMER-9");
        assertThat(record.getAmount()).isEqualByComparingTo("15.30");
    }
}
