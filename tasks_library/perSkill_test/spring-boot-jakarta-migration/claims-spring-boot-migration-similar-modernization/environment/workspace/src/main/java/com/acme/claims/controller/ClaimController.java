package com.acme.claims.controller;

import com.acme.claims.dto.ClaimRequest;
import com.acme.claims.dto.ClaimResponse;
import com.acme.claims.service.ClaimService;
import javax.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/claims")
public class ClaimController {

    private final ClaimService claimService;

    public ClaimController(ClaimService claimService) {
        this.claimService = claimService;
    }

    @PostMapping
    @PreAuthorize("hasRole('ADJUSTER')")
    public ResponseEntity<ClaimResponse> create(@Valid @RequestBody ClaimRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(claimService.createClaim(request));
    }

    @GetMapping("/{id}")
    @PreAuthorize("isAuthenticated()")
    public ClaimResponse getById(@PathVariable Long id) {
        return claimService.getClaim(id);
    }
}
