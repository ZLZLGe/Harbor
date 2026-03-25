#!/bin/bash

set -euo pipefail

cd /workspace

cat <<'EOF' > src/main/java/com/example/opsgateway/security/GatewaySecurityChains.java
package com.example.opsgateway.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.www.BasicAuthenticationFilter;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class GatewaySecurityChains {

    private final ApiTokenAuthenticationFilter apiTokenAuthenticationFilter;

    public GatewaySecurityChains(ApiTokenAuthenticationFilter apiTokenAuthenticationFilter) {
        this.apiTokenAuthenticationFilter = apiTokenAuthenticationFilter;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
        return new InMemoryUserDetailsManager(
                User.withUsername("opsbot")
                        .password(passwordEncoder.encode("ops-pass"))
                        .roles("OPS")
                        .build(),
                User.withUsername("viewer")
                        .password(passwordEncoder.encode("viewer-pass"))
                        .roles("VIEWER")
                        .build());
    }

    @Bean
    @Order(1)
    public SecurityFilterChain publicSurfaceChain(HttpSecurity http) throws Exception {
        return http
                .securityMatcher("/actuator/health", "/docs/**")
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers("/actuator/health", "/docs/**").permitAll()
                        .anyRequest().denyAll())
                .csrf(csrf -> csrf.disable())
                .requestCache(requestCache -> requestCache.disable())
                .securityContext(securityContext -> securityContext.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .build();
    }

    @Bean
    @Order(2)
    public SecurityFilterChain internalChain(HttpSecurity http) throws Exception {
        return http
                .securityMatcher("/internal/**")
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers("/internal/**").hasRole("OPS")
                        .anyRequest().denyAll())
                .httpBasic(Customizer.withDefaults())
                .csrf(csrf -> csrf.disable())
                .build();
    }

    @Bean
    @Order(3)
    public SecurityFilterChain apiChain(HttpSecurity http) throws Exception {
        return http
                .securityMatcher("/api/**")
                .authorizeHttpRequests(authorize -> authorize.anyRequest().authenticated())
                .addFilterBefore(apiTokenAuthenticationFilter, BasicAuthenticationFilter.class)
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .httpBasic(httpBasic -> httpBasic.disable())
                .formLogin(formLogin -> formLogin.disable())
                .exceptionHandling(exceptions -> exceptions.authenticationEntryPoint((request, response, exception) ->
                        response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Unauthorized")))
                .build();
    }
}
EOF

mvn -q test
