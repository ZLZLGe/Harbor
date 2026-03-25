package com.example.invoice.web;

import com.example.invoice.support.CapturingFilterChain;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

class AuditTrailFilterTest {

    private final AuditTrailFilter filter = new AuditTrailFilter();

    @Test
    void shouldExposeActorAndTraceWhenHeaderPresent() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/invoices/submit");
        request.addHeader("X-Actor", " finance-bot ");
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingFilterChain chain = new CapturingFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(chain.wasInvoked()).isTrue();
        assertThat(request.getAttribute("audit.actor")).isEqualTo("finance-bot");
        assertThat(response.getHeader("X-Audit-Trace")).isEqualTo("POST:/api/invoices/submit:finance-bot");
    }

    @Test
    void shouldFallbackToAnonymousWhenHeaderMissing() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/invoices/42");
        MockHttpServletResponse response = new MockHttpServletResponse();
        CapturingFilterChain chain = new CapturingFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(chain.wasInvoked()).isTrue();
        assertThat(request.getAttribute("audit.actor")).isEqualTo("anonymous");
        assertThat(response.getHeader("X-Audit-Trace")).isEqualTo("GET:/api/invoices/42:anonymous");
    }
}
