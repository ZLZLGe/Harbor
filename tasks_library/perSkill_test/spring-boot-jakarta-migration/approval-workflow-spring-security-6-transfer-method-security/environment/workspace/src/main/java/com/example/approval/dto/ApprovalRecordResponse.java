package com.example.approval.dto;

public record ApprovalRecordResponse(
    long documentId,
    String title,
    String submitter,
    String approver,
    String state,
    String actedBy
) {
}
