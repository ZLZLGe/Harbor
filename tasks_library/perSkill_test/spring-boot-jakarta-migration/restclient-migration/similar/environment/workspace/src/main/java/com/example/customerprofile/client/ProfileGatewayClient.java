package com.example.customerprofile.client;

import com.example.customerprofile.dto.CustomerProfile;
import com.example.customerprofile.dto.WelcomeMessageRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;

@Service
public class ProfileGatewayClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public ProfileGatewayClient(@Value("${profile.api.base-url}") String baseUrl) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public CustomerProfile fetchProfile(String customerId) {
        return restTemplate.getForObject(
                baseUrl + "/profiles/" + customerId,
                CustomerProfile.class
        );
    }

    public void sendWelcomeMessage(String customerId, String templateCode) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));

        WelcomeMessageRequest payload = new WelcomeMessageRequest(customerId, templateCode);
        HttpEntity<WelcomeMessageRequest> request = new HttpEntity<>(payload, headers);

        restTemplate.postForEntity(
                baseUrl + "/notifications/welcome",
                request,
                Void.class
        );
    }

    public boolean deleteSnapshot(String customerId) {
        try {
            restTemplate.delete(baseUrl + "/snapshots/" + customerId);
            return true;
        } catch (RuntimeException ex) {
            return false;
        }
    }
}
