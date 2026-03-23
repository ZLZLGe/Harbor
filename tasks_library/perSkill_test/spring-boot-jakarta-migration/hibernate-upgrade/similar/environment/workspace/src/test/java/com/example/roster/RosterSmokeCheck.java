package com.example.roster;

import com.example.roster.controller.UserRosterController;
import com.example.roster.dto.UserSignupRequest;
import com.example.roster.filter.CorrelationIdFilter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

public class RosterSmokeCheck {
    public static void main(String[] args) throws Exception {
        UserSignupRequest request = new UserSignupRequest();
        request.setEmployeeId("EMP-100");
        request.setEmail("person@example.com");

        Map<String, String> result = new UserRosterController().signup(request);
        if (!"EMP-100".equals(result.get("employeeId"))) {
            throw new AssertionError("controller output mismatch");
        }

        CorrelationIdFilter filter = new CorrelationIdFilter();
        MockRequest mockRequest = new MockRequest("/api/roster/signup");
        MockResponse mockResponse = new MockResponse();
        RecordingChain chain = new RecordingChain();
        filter.doFilter(mockRequest, mockResponse, chain);
        if (!chain.called) {
            throw new AssertionError("filter chain not invoked");
        }
        if (!"/api/roster/signup".equals(mockResponse.headers.get("X-Correlation-Source"))) {
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
