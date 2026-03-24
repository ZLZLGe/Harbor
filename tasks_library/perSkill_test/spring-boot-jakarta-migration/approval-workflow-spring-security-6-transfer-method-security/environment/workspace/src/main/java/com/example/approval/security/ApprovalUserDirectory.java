package com.example.approval.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;

@Configuration
public class ApprovalUserDirectory {

    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
        return new InMemoryUserDetailsManager(
            User.withUsername("submitter.alice")
                .password(passwordEncoder.encode("submit-pass"))
                .roles("SUBMITTER")
                .build(),
            User.withUsername("submitter.bob")
                .password(passwordEncoder.encode("submit-pass"))
                .roles("SUBMITTER")
                .build(),
            User.withUsername("approver.nina")
                .password(passwordEncoder.encode("approve-pass"))
                .roles("APPROVER")
                .build(),
            User.withUsername("approver.otto")
                .password(passwordEncoder.encode("approve-pass"))
                .roles("APPROVER")
                .build(),
            User.withUsername("supervisor.maya")
                .password(passwordEncoder.encode("super-pass"))
                .roles("SUPERVISOR")
                .build()
        );
    }
}
