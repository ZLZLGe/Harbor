package com.example.opsgateway.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.config.annotation.method.configuration.EnableGlobalMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.authentication.www.BasicAuthenticationFilter;

@Configuration
@EnableWebSecurity
@EnableGlobalMethodSecurity(prePostEnabled = true)
public class GatewaySecurityChains {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService() {
        return new InMemoryUserDetailsManager(
                User.withUsername("opsbot")
                        .password(passwordEncoder().encode("ops-pass"))
                        .roles("OPS")
                        .build(),
                User.withUsername("viewer")
                        .password(passwordEncoder().encode("viewer-pass"))
                        .roles("VIEWER")
                        .build());
    }

    @Configuration
    @Order(1)
    static class PublicEndpointsSecurity extends WebSecurityConfigurerAdapter {

        @Override
        protected void configure(HttpSecurity http) throws Exception {
            http
                    .requestMatchers()
                    .antMatchers("/actuator/health", "/docs/**")
                    .and()
                    .authorizeRequests()
                    .antMatchers("/actuator/health", "/docs/**")
                    .permitAll()
                    .anyRequest()
                    .denyAll();
        }
    }

    @Configuration
    @Order(2)
    static class InternalEndpointsSecurity extends WebSecurityConfigurerAdapter {

        private final UserDetailsService userDetailsService;
        private final PasswordEncoder passwordEncoder;

        InternalEndpointsSecurity(UserDetailsService userDetailsService, PasswordEncoder passwordEncoder) {
            this.userDetailsService = userDetailsService;
            this.passwordEncoder = passwordEncoder;
        }

        @Override
        protected void configure(AuthenticationManagerBuilder auth) throws Exception {
            auth.userDetailsService(userDetailsService).passwordEncoder(passwordEncoder);
        }

        @Override
        protected void configure(HttpSecurity http) throws Exception {
            http
                    .antMatcher("/internal/**")
                    .csrf()
                    .disable()
                    .authorizeRequests()
                    .antMatchers("/internal/**")
                    .hasRole("OPS")
                    .and()
                    .httpBasic();
        }
    }

    @Configuration
    @Order(3)
    static class ApiEndpointsSecurity extends WebSecurityConfigurerAdapter {

        private final ApiTokenAuthenticationFilter apiTokenAuthenticationFilter;

        ApiEndpointsSecurity(ApiTokenAuthenticationFilter apiTokenAuthenticationFilter) {
            this.apiTokenAuthenticationFilter = apiTokenAuthenticationFilter;
        }

        @Override
        protected void configure(HttpSecurity http) throws Exception {
            http
                    .antMatcher("/api/**")
                    .csrf()
                    .disable()
                    .sessionManagement()
                    .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                    .and()
                    .addFilterBefore(apiTokenAuthenticationFilter, BasicAuthenticationFilter.class)
                    .exceptionHandling()
                    .authenticationEntryPoint((request, response, exception) ->
                            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Unauthorized"))
                    .and()
                    .authorizeRequests()
                    .anyRequest()
                    .authenticated();
        }
    }
}
