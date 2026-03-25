package com.example.invoice.support;

import java.io.IOException;
import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;

public class CapturingFilterChain implements FilterChain {

    private boolean invoked;
    private ServletRequest lastRequest;
    private ServletResponse lastResponse;

    @Override
    public void doFilter(ServletRequest request, ServletResponse response) throws IOException, ServletException {
        this.invoked = true;
        this.lastRequest = request;
        this.lastResponse = response;
    }

    public boolean wasInvoked() {
        return invoked;
    }

    public ServletRequest getLastRequest() {
        return lastRequest;
    }

    public ServletResponse getLastResponse() {
        return lastResponse;
    }
}
