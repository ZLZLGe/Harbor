package com.example.clinic;

import com.example.clinic.config.IntakeBootstrap;
import com.example.clinic.controller.PatientIntakeController;
import com.example.clinic.dto.PatientIntakeRequest;
import com.example.clinic.filter.RequestAuditFilter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

public class ClinicSmokeCheck {
    public static void main(String[] args) throws Exception {
        new IntakeBootstrap().init();
        if (!"true".equals(System.getProperty("clinic.bootstrap.ready"))) {
            throw new AssertionError("bootstrap did not run");
        }

        PatientIntakeRequest request = new PatientIntakeRequest();
        request.setPatientCode("PAT-7");
        request.setSymptomSummary("mild cough");
        Map<String, String> result = new PatientIntakeController().submit(request);
        if (!"PAT-7".equals(result.get("patientCode"))) {
            throw new AssertionError("controller output mismatch");
        }

        RequestAuditFilter filter = new RequestAuditFilter();
        MockRequest mockRequest = new MockRequest("/api/intake");
        MockResponse mockResponse = new MockResponse();
        RecordingChain chain = new RecordingChain();
        filter.doFilter(mockRequest, mockResponse, chain);
        if (!chain.called) {
            throw new AssertionError("filter chain not invoked");
        }
        if (!"/api/intake".equals(mockResponse.headers.get("X-Clinic-Path"))) {
            throw new AssertionError("filter header missing");
        }
    }

    static final class MockRequest implements HttpServletRequest {
        private final String uri;

        MockRequest(String uri) {
            this.uri = uri;
        }

        @Override
        public String getRequestURI() {
            return uri;
        }
    }

    static final class MockResponse implements HttpServletResponse {
        final Map<String, String> headers = new HashMap<>();

        @Override
        public void setHeader(String name, String value) {
            headers.put(name, value);
        }
    }

    static final class RecordingChain implements FilterChain {
        boolean called;

        @Override
        public void doFilter(HttpServletRequest request, HttpServletResponse response)
                throws IOException, ServletException {
            called = true;
        }
    }
}
