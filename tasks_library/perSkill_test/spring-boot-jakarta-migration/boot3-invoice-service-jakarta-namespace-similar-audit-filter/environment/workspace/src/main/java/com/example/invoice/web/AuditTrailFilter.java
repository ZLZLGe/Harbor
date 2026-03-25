package com.example.invoice.web;

import java.io.IOException;
import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class AuditTrailFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {
        String actor = resolveActor(request.getHeader("X-Actor"));
        request.setAttribute("audit.actor", actor);
        response.setHeader("X-Audit-Trace", request.getMethod() + ":" + request.getRequestURI() + ":" + actor);
        filterChain.doFilter(request, response);
    }

    private String resolveActor(String actorHeader) {
        if (actorHeader == null || actorHeader.isBlank()) {
            return "anonymous";
        }
        return actorHeader.trim();
    }
}
