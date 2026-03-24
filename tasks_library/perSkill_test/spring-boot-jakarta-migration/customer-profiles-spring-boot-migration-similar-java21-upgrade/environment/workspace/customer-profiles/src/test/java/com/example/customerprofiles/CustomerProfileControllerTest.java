package com.example.customerprofiles;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class CustomerProfileControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void listsProfiles() throws Exception {
        mockMvc.perform(get("/profiles"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].companyName").value("Harbor Retail"))
            .andExpect(jsonPath("$[1].city").value("Singapore"));
    }

    @Test
    void findsProfileById() throws Exception {
        mockMvc.perform(get("/profiles/2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.companyName").value("Northwind Labs"))
            .andExpect(jsonPath("$.segment").value("mid-market"));
    }
}
