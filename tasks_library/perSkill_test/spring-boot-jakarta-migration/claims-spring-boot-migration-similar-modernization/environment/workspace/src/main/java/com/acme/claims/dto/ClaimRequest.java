package com.acme.claims.dto;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

public class ClaimRequest {

    @NotBlank
    private String policyNumber;

    @NotBlank
    @Email
    private String claimantEmail;

    @NotBlank
    @Size(min = 10, max = 200)
    private String description;

    public String getPolicyNumber() {
        return policyNumber;
    }

    public void setPolicyNumber(String policyNumber) {
        this.policyNumber = policyNumber;
    }

    public String getClaimantEmail() {
        return claimantEmail;
    }

    public void setClaimantEmail(String claimantEmail) {
        this.claimantEmail = claimantEmail;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }
}
