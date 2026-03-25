package com.example.approval.service;

import com.example.approval.model.ApprovalAction;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

@Service
public class DocumentApprovalService {

    @PreAuthorize("hasRole('AUTHOR')")
    public ApprovalAction submit(String documentId) {
        return action(documentId, "SUBMITTED");
    }

    @PreAuthorize("hasRole('APPROVER')")
    public ApprovalAction approve(String documentId) {
        return action(documentId, "APPROVED");
    }

    @PreAuthorize("hasAnyRole('APPROVER', 'AUDITOR')")
    public String readAuditTrail(String documentId) {
        return "audit:" + documentId + ":" + currentUser();
    }

    private ApprovalAction action(String documentId, String action) {
        return new ApprovalAction(documentId, action, currentUser());
    }

    private String currentUser() {
        return SecurityContextHolder.getContext().getAuthentication().getName();
    }
}
