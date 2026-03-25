package com.example.opsgateway.security;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.stereotype.Service;

@Service
public class GatewayTokenService {

    public Authentication authenticate(String token) {
        return switch (token) {
            case "ops-api-token" -> new UsernamePasswordAuthenticationToken(
                    "api-robot",
                    token,
                    AuthorityUtils.createAuthorityList("ROLE_API_CLIENT", "SCOPE_transfers.read"));
            case "readonly-api-token" -> new UsernamePasswordAuthenticationToken(
                    "readonly-robot",
                    token,
                    AuthorityUtils.createAuthorityList("SCOPE_transfers.read"));
            default -> null;
        };
    }
}
