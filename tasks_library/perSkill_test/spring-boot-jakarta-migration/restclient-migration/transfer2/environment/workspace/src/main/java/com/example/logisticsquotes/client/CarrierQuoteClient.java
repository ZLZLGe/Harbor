package com.example.logisticsquotes.client;

import com.example.logisticsquotes.dto.CarrierQuote;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;

@Service
public class CarrierQuoteClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public CarrierQuoteClient(@Value("${quotes.api.base-url}") String baseUrl) {
        this.baseUrl = baseUrl;
        this.restTemplate = new RestTemplate();
    }

    public List<CarrierQuote> lookupQuotes(String origin, String destination, int weightKg) {
        HttpHeaders headers = new HttpHeaders();
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        HttpEntity<Void> request = new HttpEntity<>(headers);

        ResponseEntity<List<CarrierQuote>> response = restTemplate.exchange(
                baseUrl + "/quotes/search?origin={origin}&destination={destination}&weightKg={weightKg}",
                HttpMethod.GET,
                request,
                new ParameterizedTypeReference<List<CarrierQuote>>() {
                },
                origin,
                destination,
                weightKg
        );

        return response.getBody() == null ? List.of() : response.getBody();
    }

    public void cancelQuote(String quoteRequestId) {
        restTemplate.delete(baseUrl + "/quotes/requests/" + quoteRequestId);
    }
}
