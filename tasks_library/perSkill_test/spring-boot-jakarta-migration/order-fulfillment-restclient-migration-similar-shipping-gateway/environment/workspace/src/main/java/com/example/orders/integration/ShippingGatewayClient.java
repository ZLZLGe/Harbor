package com.example.orders.integration;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class ShippingGatewayClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public ShippingGatewayClient(
        @Value("${shipping.gateway.base-url:https://shipping.example.internal}") String baseUrl
    ) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public ShippingQuote fetchQuote(String destinationZip, BigDecimal declaredValue) {
        HttpEntity<Void> request = new HttpEntity<>(jsonHeaders());
        ResponseEntity<ShippingQuote> response = restTemplate.exchange(
            baseUrl + "/shipping/quotes?destinationZip={destinationZip}&declaredValue={declaredValue}",
            HttpMethod.GET,
            request,
            ShippingQuote.class,
            destinationZip,
            declaredValue
        );
        return response.getBody();
    }

    public ShipmentResponse createShipment(ShipmentRequest shipmentRequest) {
        HttpEntity<ShipmentRequest> request = new HttpEntity<>(shipmentRequest, jsonHeaders());
        ResponseEntity<ShipmentResponse> response = restTemplate.postForEntity(
            baseUrl + "/shipping/shipments",
            request,
            ShipmentResponse.class
        );
        return response.getBody();
    }

    public void cancelShipment(String shipmentId, String reason) {
        HttpEntity<Void> request = new HttpEntity<>(jsonHeaders());
        restTemplate.exchange(
            baseUrl + "/shipping/shipments/{shipmentId}?reason={reason}",
            HttpMethod.DELETE,
            request,
            Void.class,
            shipmentId,
            reason
        );
    }

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.setContentType(MediaType.APPLICATION_JSON);
        return headers;
    }
}
