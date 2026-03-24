package com.example.memberdirectory.controller;

import java.util.Map;

import com.example.memberdirectory.dto.MemberStatusUpdate;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class DirectoryController {

    @GetMapping("/api/members/{memberId}")
    @PreAuthorize("hasAnyRole('ADMIN','REVIEWER') or @memberAccess.isOwner(authentication, #memberId)")
    public ResponseEntity<Map<String, Object>> getMember(@PathVariable Long memberId) {
        return ResponseEntity.ok(Map.of(
            "memberId", memberId,
            "displayName", "member-" + memberId
        ));
    }

    @PatchMapping("/api/members/{memberId}/status")
    @PreAuthorize("hasAnyRole('ADMIN','REVIEWER')")
    public ResponseEntity<Map<String, Object>> updateStatus(
        @PathVariable Long memberId,
        @Valid @RequestBody MemberStatusUpdate update
    ) {
        return ResponseEntity.ok(Map.of(
            "memberId", memberId,
            "status", update.status()
        ));
    }

    @DeleteMapping("/api/members/{memberId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteMember(@PathVariable Long memberId) {
        return ResponseEntity.noContent().build();
    }
}
