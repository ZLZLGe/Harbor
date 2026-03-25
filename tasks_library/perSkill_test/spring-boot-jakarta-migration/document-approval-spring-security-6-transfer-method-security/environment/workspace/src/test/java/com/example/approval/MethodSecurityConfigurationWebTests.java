package com.example.approval;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MethodSecurityConfigurationWebTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    void loginEndpointIsPublic() throws Exception {
        mockMvc.perform(post("/api/session/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of("username", "delta"))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.user").value("delta"))
            .andExpect(jsonPath("$.sessionToken").value("session-delta"));
    }

    @Test
    void actuatorHealthIsPublic() throws Exception {
        mockMvc.perform(get("/actuator/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void anonymousUserCannotReadProtectedDocument() throws Exception {
        mockMvc.perform(get("/api/documents/DOC-22"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void authenticatedUserCanReadProtectedDocument() throws Exception {
        mockMvc.perform(get("/api/documents/DOC-22")
                .with(SecurityMockMvcRequestPostProcessors.user("approver.casey").roles("APPROVER")))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.documentId").value("DOC-22"))
            .andExpect(jsonPath("$.status").value("IN_REVIEW"));
    }
}
