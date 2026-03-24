package com.example.memberdirectory.security;

import java.util.Map;

import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class DirectoryUserDetailsService implements UserDetailsService {

    private final Map<String, UserDetails> users;

    public DirectoryUserDetailsService(PasswordEncoder passwordEncoder) {
        this.users = Map.of(
            "admin", User.withUsername("admin")
                .password(passwordEncoder.encode("admin-pass"))
                .roles("ADMIN")
                .build(),
            "reviewer", User.withUsername("reviewer")
                .password(passwordEncoder.encode("review-pass"))
                .roles("REVIEWER")
                .build(),
            "member-7", User.withUsername("member-7")
                .password(passwordEncoder.encode("alice-pass"))
                .roles("MEMBER")
                .build(),
            "member-9", User.withUsername("member-9")
                .password(passwordEncoder.encode("bob-pass"))
                .roles("MEMBER")
                .build()
        );
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        UserDetails user = users.get(username);
        if (user == null) {
            throw new UsernameNotFoundException("Unknown member: " + username);
        }
        return user;
    }
}
