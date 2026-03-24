package com.example.memberdirectory;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
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
class SecurityBehaviorTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void registerEndpointIsPublic() throws Exception {
        mockMvc.perform(post("/api/members/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"displayName":"new member","email":"new.member@example.com"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("accepted"));
    }

    @Test
    void loginEndpointUsesAuthenticationManager() throws Exception {
        mockMvc.perform(post("/api/session/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"username":"reviewer","password":"review-pass"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.username").value("reviewer"));
    }

    @Test
    void healthEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/actuator/health"))
            .andExpect(status().isOk());
    }

    @Test
    void memberCanReadOwnEntry() throws Exception {
        mockMvc.perform(get("/api/members/7")
                .with(user("member-7").roles("MEMBER")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.memberId").value(7));
    }

    @Test
    void memberCannotReadAnotherEntry() throws Exception {
        mockMvc.perform(get("/api/members/9")
                .with(user("member-7").roles("MEMBER")))
            .andExpect(status().isForbidden());
    }

    @Test
    void reviewerCanUpdateStatus() throws Exception {
        mockMvc.perform(patch("/api/members/7/status")
                .with(user("reviewer").roles("REVIEWER"))
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"status":"APPROVED"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("APPROVED"));
    }

    @Test
    void adminCanDeleteMember() throws Exception {
        mockMvc.perform(delete("/api/members/7")
                .with(user("admin").roles("ADMIN"))
                .with(csrf()))
            .andExpect(status().isNoContent());
    }

    @Test
    void reviewerCannotDeleteMember() throws Exception {
        mockMvc.perform(delete("/api/members/7")
                .with(user("reviewer").roles("REVIEWER"))
                .with(csrf()))
            .andExpect(status().isForbidden());
    }
}
