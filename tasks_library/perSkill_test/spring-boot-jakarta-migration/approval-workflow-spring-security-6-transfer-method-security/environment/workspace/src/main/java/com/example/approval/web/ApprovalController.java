package com.example.approval.web;

import java.security.Principal;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.example.approval.dto.ApprovalDecisionRequest;
import com.example.approval.dto.ApprovalRecordResponse;
import com.example.approval.security.ApprovalPolicy;

@RestController
@RequestMapping("/api/approvals")
public class ApprovalController {

    private final ApprovalPolicy approvalPolicy;

    public ApprovalController(ApprovalPolicy approvalPolicy) {
        this.approvalPolicy = approvalPolicy;
    }

    @GetMapping("/{documentId}")
    @PreAuthorize("hasRole('SUPERVISOR') or @approvalPolicy.canView(authentication, #documentId)")
    public ApprovalRecordResponse viewApproval(@PathVariable long documentId) {
        return approvalPolicy.currentRecord(documentId);
    }

    @PostMapping("/{documentId}/decision")
    @PreAuthorize("@approvalPolicy.canApprove(authentication, #documentId)")
    public ApprovalRecordResponse recordDecision(
        @PathVariable long documentId,
        @RequestBody ApprovalDecisionRequest request,
        Principal principal
    ) {
        return approvalPolicy.decidedRecord(documentId, request.decision(), principal.getName());
    }

    @PostMapping("/{documentId}/resubmit")
    @PreAuthorize("hasRole('SUBMITTER') and @approvalPolicy.isSubmitter(authentication, #documentId)")
    public ApprovalRecordResponse resubmitApproval(@PathVariable long documentId, Principal principal) {
        return approvalPolicy.resubmittedRecord(documentId, principal.getName());
    }
}
