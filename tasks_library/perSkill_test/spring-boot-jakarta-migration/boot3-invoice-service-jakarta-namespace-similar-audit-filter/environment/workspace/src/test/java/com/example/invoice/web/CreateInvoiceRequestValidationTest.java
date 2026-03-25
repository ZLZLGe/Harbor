package com.example.invoice.web;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.math.BigDecimal;
import java.util.Set;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class CreateInvoiceRequestValidationTest {

    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    @Test
    void shouldRejectBlankAndMissingFields() {
        CreateInvoiceRequest request = new CreateInvoiceRequest();
        request.setInvoiceNumber(" ");
        request.setCustomerCode("");
        request.setAmount(BigDecimal.ZERO);

        Set<String> invalidFields = validator.validate(request).stream()
                .map(violation -> violation.getPropertyPath().toString())
                .collect(java.util.stream.Collectors.toSet());

        assertThat(invalidFields).contains("invoiceNumber", "customerCode", "amount");
    }
}
