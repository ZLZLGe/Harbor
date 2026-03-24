package com.example.approval;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class ApprovalWorkflowSecurityTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/actuator/health"))
            .andExpect(status().isOk());
    }

    @Test
    void approvalRoutesRequireAuthentication() throws Exception {
        mockMvc.perform(get("/api/approvals/1001"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void submitterCanViewOwnDocument() throws Exception {
        mockMvc.perform(get("/api/approvals/1001")
                .with(httpBasic("submitter.alice", "submit-pass")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.documentId").value(1001))
            .andExpect(jsonPath("$.submitter").value("submitter.alice"));
    }

    @Test
    void submitterCannotViewAnotherSubmittersDocument() throws Exception {
        mockMvc.perform(get("/api/approvals/1001")
                .with(httpBasic("submitter.bob", "submit-pass")))
            .andExpect(status().isForbidden());
    }

    @Test
    void assignedApproverCanRecordDecision() throws Exception {
        mockMvc.perform(post("/api/approvals/1001/decision")
                .with(httpBasic("approver.nina", "approve-pass"))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"decision":"APPROVED","comment":"Ready for release"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.state").value("APPROVED"))
            .andExpect(jsonPath("$.actedBy").value("approver.nina"));
    }

    @Test
    void unrelatedApproverCannotRecordDecision() throws Exception {
        mockMvc.perform(post("/api/approvals/1002/decision")
                .with(httpBasic("approver.nina", "approve-pass"))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"decision":"REJECTED","comment":"Wrong queue"}
                    """))
            .andExpect(status().isForbidden());
    }

    @Test
    void supervisorCanDecideAnyDocument() throws Exception {
        mockMvc.perform(post("/api/approvals/1002/decision")
                .with(httpBasic("supervisor.maya", "super-pass"))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"decision":"APPROVED","comment":"Escalated approval"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.state").value("APPROVED"))
            .andExpect(jsonPath("$.actedBy").value("supervisor.maya"));
    }

    @Test
    void submitterCanResubmitOwnDocument() throws Exception {
        mockMvc.perform(post("/api/approvals/1001/resubmit")
                .with(httpBasic("submitter.alice", "submit-pass")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.state").value("RESUBMITTED"))
            .andExpect(jsonPath("$.actedBy").value("submitter.alice"));
    }

    @Test
    void approverCannotResubmitDocument() throws Exception {
        mockMvc.perform(post("/api/approvals/1001/resubmit")
                .with(httpBasic("approver.nina", "approve-pass")))
            .andExpect(status().isForbidden());
    }
}
