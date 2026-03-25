package com.acme.claims.controller;

import com.acme.claims.dto.ClaimRequest;
import com.acme.claims.dto.ClaimResponse;
import com.acme.claims.model.ClaimStatus;
import com.acme.claims.service.ClaimService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ClaimControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private ClaimService claimService;

    @Test
    void healthEndpointRemainsPublic() throws Exception {
        mockMvc.perform(get("/api/public/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void claimLookupRequiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/claims/42"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(username = "adjuster", roles = "ADJUSTER")
    void adjusterCanCreateClaim() throws Exception {
        ClaimResponse response = new ClaimResponse();
        response.setId(7L);
        response.setPolicyNumber("PN-100");
        response.setClaimantEmail("adjuster@acme.test");
        response.setDescription("Vehicle accident at loading dock");
        response.setStatus(ClaimStatus.IN_REVIEW);
        response.setFlaggedForReview(true);
        response.setRiskScore(91);

        when(claimService.createClaim(any(ClaimRequest.class))).thenReturn(response);

        ClaimRequest request = new ClaimRequest();
        request.setPolicyNumber("PN-100");
        request.setClaimantEmail("adjuster@acme.test");
        request.setDescription("Vehicle accident at loading dock");

        mockMvc.perform(post("/api/claims")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("IN_REVIEW"))
                .andExpect(jsonPath("$.riskScore").value(91));
    }

    @Test
    @WithMockUser(username = "reviewer", roles = "REVIEWER")
    void reviewerCannotCreateClaim() throws Exception {
        ClaimRequest request = new ClaimRequest();
        request.setPolicyNumber("PN-101");
        request.setClaimantEmail("reviewer@acme.test");
        request.setDescription("Warehouse water damage event");

        mockMvc.perform(post("/api/claims")
                        .contentType("application/json")
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isForbidden());
    }
}
