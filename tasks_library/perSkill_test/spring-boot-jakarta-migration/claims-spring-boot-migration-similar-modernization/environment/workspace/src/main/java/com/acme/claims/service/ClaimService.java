package com.acme.claims.service;

import com.acme.claims.dto.ClaimRequest;
import com.acme.claims.dto.ClaimResponse;
import com.acme.claims.model.Claim;
import com.acme.claims.model.ClaimStatus;
import com.acme.claims.repository.ClaimRepository;
import org.springframework.stereotype.Service;

@Service
public class ClaimService {

    private final ClaimRepository claimRepository;
    private final RiskGateway riskGateway;

    public ClaimService(ClaimRepository claimRepository, RiskGateway riskGateway) {
        this.claimRepository = claimRepository;
        this.riskGateway = riskGateway;
    }

    public ClaimResponse createClaim(ClaimRequest request) {
        RiskDecision riskDecision = riskGateway.evaluate(request.getPolicyNumber(), request.getClaimantEmail());

        Claim claim = new Claim();
        claim.setPolicyNumber(request.getPolicyNumber());
        claim.setClaimantEmail(request.getClaimantEmail());
        claim.setDescription(request.getDescription());
        claim.setRiskScore(riskDecision.getScore());
        claim.setFlaggedForReview(riskDecision.isManualReviewRequired());
        claim.setStatus(riskDecision.isManualReviewRequired() ? ClaimStatus.IN_REVIEW : ClaimStatus.OPEN);

        return toResponse(claimRepository.save(claim));
    }

    public ClaimResponse getClaim(Long id) {
        Claim claim = claimRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Claim not found"));
        return toResponse(claim);
    }

    private ClaimResponse toResponse(Claim claim) {
        ClaimResponse response = new ClaimResponse();
        response.setId(claim.getId());
        response.setPolicyNumber(claim.getPolicyNumber());
        response.setClaimantEmail(claim.getClaimantEmail());
        response.setDescription(claim.getDescription());
        response.setStatus(claim.getStatus());
        response.setFlaggedForReview(claim.isFlaggedForReview());
        response.setRiskScore(claim.getRiskScore());
        return response;
    }
}
