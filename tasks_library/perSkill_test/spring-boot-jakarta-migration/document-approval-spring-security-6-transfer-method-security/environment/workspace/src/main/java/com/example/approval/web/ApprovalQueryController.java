package com.example.approval.web;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/documents")
public class ApprovalQueryController {

    @GetMapping("/{documentId}")
    public Map<String, String> getDocument(@PathVariable String documentId) {
        return Map.of(
            "documentId", documentId,
            "status", "IN_REVIEW",
            "owner", "author-team"
        );
    }
}
