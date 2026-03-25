package com.example.approval;

import com.example.approval.model.ApprovalAction;
import com.example.approval.service.DocumentApprovalService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@ActiveProfiles("test")
class DocumentApprovalServiceSecurityTests {

    @Autowired
    private DocumentApprovalService documentApprovalService;

    @Test
    @WithMockUser(username = "author.alex", roles = "AUTHOR")
    void authorCanSubmitDocument() {
        ApprovalAction action = documentApprovalService.submit("DOC-17");

        assertThat(action.documentId()).isEqualTo("DOC-17");
        assertThat(action.action()).isEqualTo("SUBMITTED");
        assertThat(action.actor()).isEqualTo("author.alex");
    }

    @Test
    @WithMockUser(username = "audit.ash", roles = "AUDITOR")
    void auditorCannotSubmitDocument() {
        assertThatThrownBy(() -> documentApprovalService.submit("DOC-17"))
            .isInstanceOf(AccessDeniedException.class);
    }

    @Test
    @WithMockUser(username = "approver.casey", roles = "APPROVER")
    void approverCanApproveDocument() {
        ApprovalAction action = documentApprovalService.approve("DOC-33");

        assertThat(action.documentId()).isEqualTo("DOC-33");
        assertThat(action.action()).isEqualTo("APPROVED");
        assertThat(action.actor()).isEqualTo("approver.casey");
    }

    @Test
    @WithMockUser(username = "author.alex", roles = "AUTHOR")
    void authorCannotApproveDocument() {
        assertThatThrownBy(() -> documentApprovalService.approve("DOC-33"))
            .isInstanceOf(AccessDeniedException.class);
    }

    @Test
    @WithMockUser(username = "audit.ash", roles = "AUDITOR")
    void auditorCanReadAuditTrail() {
        assertThat(documentApprovalService.readAuditTrail("DOC-44"))
            .isEqualTo("audit:DOC-44:audit.ash");
    }
}
