package com.example.memberdirectory.security;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

@Component("memberAccess")
public class MemberAccess {

    public boolean isOwner(Authentication authentication, Long memberId) {
        return authentication != null
            && authentication.isAuthenticated()
            && ("member-" + memberId).equals(authentication.getName());
    }
}
