package com.example.approval.security;

import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import com.example.approval.dto.ApprovalRecordResponse;

@Component("approvalPolicy")
public class ApprovalPolicy {

    private final Map<Long, WorkflowDocument> documents = Map.of(
        1001L, new WorkflowDocument("Vendor onboarding packet", "submitter.alice", "approver.nina"),
        1002L, new WorkflowDocument("Quarterly budget exception", "submitter.bob", "approver.otto")
    );

    public boolean canView(Authentication authentication, long documentId) {
        if (hasRole(authentication, "SUPERVISOR")) {
            return true;
        }

        WorkflowDocument document = documents.get(documentId);
        return document != null && (
            hasRole(authentication, "SUBMITTER") && document.submitter().equals(authentication.getName())
                || hasRole(authentication, "APPROVER") && document.approver().equals(authentication.getName())
        );
    }

    public boolean canApprove(Authentication authentication, long documentId) {
        if (hasRole(authentication, "SUPERVISOR")) {
            return true;
        }

        WorkflowDocument document = documents.get(documentId);
        return document != null
            && hasRole(authentication, "APPROVER")
            && document.approver().equals(authentication.getName());
    }

    public boolean isSubmitter(Authentication authentication, long documentId) {
        WorkflowDocument document = documents.get(documentId);
        return document != null
            && hasRole(authentication, "SUBMITTER")
            && document.submitter().equals(authentication.getName());
    }

    public ApprovalRecordResponse currentRecord(long documentId) {
        WorkflowDocument document = requireDocument(documentId);
        return new ApprovalRecordResponse(
            documentId,
            document.title(),
            document.submitter(),
            document.approver(),
            "PENDING",
            "workflow-system"
        );
    }

    public ApprovalRecordResponse decidedRecord(long documentId, String decision, String actedBy) {
        WorkflowDocument document = requireDocument(documentId);
        return new ApprovalRecordResponse(
            documentId,
            document.title(),
            document.submitter(),
            document.approver(),
            decision,
            actedBy
        );
    }

    public ApprovalRecordResponse resubmittedRecord(long documentId, String actedBy) {
        WorkflowDocument document = requireDocument(documentId);
        return new ApprovalRecordResponse(
            documentId,
            document.title(),
            document.submitter(),
            document.approver(),
            "RESUBMITTED",
            actedBy
        );
    }

    private WorkflowDocument requireDocument(long documentId) {
        WorkflowDocument document = documents.get(documentId);
        if (document == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Document not found");
        }
        return document;
    }

    private boolean hasRole(Authentication authentication, String role) {
        return authentication.getAuthorities().stream()
            .anyMatch(authority -> authority.getAuthority().equals("ROLE_" + role));
    }

    private record WorkflowDocument(String title, String submitter, String approver) {
    }
}
