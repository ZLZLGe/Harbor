package com.acme.claims.service;

import com.acme.claims.dto.ClaimRequest;
import com.acme.claims.dto.ClaimResponse;
import com.acme.claims.model.Claim;
import com.acme.claims.model.ClaimStatus;
import com.acme.claims.repository.ClaimRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ClaimServiceTest {

    @Mock
    private ClaimRepository claimRepository;

    @Mock
    private RiskGateway riskGateway;

    @InjectMocks
    private ClaimService claimService;

    @Test
    void createClaimCarriesRiskDecisionIntoResponse() {
        ClaimRequest request = new ClaimRequest();
        request.setPolicyNumber("CLM-2024-001");
        request.setClaimantEmail("customer@acme.test");
        request.setDescription("Severe storm damage on the storefront");

        when(riskGateway.evaluate("CLM-2024-001", "customer@acme.test"))
                .thenReturn(new RiskDecision(88, true));
        when(claimRepository.save(any(Claim.class))).thenAnswer(invocation -> {
            Claim claim = invocation.getArgument(0);
            claim.setId(15L);
            return claim;
        });

        ClaimResponse response = claimService.createClaim(request);

        assertThat(response.getId()).isEqualTo(15L);
        assertThat(response.getStatus()).isEqualTo(ClaimStatus.IN_REVIEW);
        assertThat(response.isFlaggedForReview()).isTrue();
        assertThat(response.getRiskScore()).isEqualTo(88);
    }
}
