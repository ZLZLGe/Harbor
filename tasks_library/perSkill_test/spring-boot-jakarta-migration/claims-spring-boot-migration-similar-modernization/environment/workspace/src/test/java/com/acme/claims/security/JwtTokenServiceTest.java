package com.acme.claims.security;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class JwtTokenServiceTest {

    @Test
    void generatedTokenKeepsSubjectAndRole() {
        JwtTokenService service = new JwtTokenService("claims-secret-key-claims-secret-key", 3600);

        String token = service.generateToken("adjuster", "ADJUSTER");

        assertThat(service.isValid(token)).isTrue();
        assertThat(service.extractUsername(token)).isEqualTo("adjuster");
        assertThat(service.extractRole(token)).isEqualTo("ADJUSTER");
    }
}
