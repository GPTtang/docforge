package com.docforge.service;

import com.docforge.model.ConvertResponse;
import com.docforge.util.MultipartInputStreamFileResource;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;

@Service
@Slf4j
public class DocConvertService {

    @Value("${docforge.python.service-url}")
    private String pythonServiceUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public DocConvertService(RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    public String convertToMarkdown(MultipartFile file) {
        ConvertResponse response = callPythonService(file, "/convert/markdown");
        if (response.getMarkdown() == null) {
            throw new PythonServiceException(
                HttpStatus.BAD_GATEWAY.value(),
                "Python service missing field: markdown"
            );
        }
        return response.getMarkdown();
    }

    public JsonNode convertToJson(MultipartFile file) {
        ConvertResponse response = callPythonService(file, "/convert/json");
        if (response.getData() == null || response.getData().isNull()) {
            throw new PythonServiceException(
                HttpStatus.BAD_GATEWAY.value(),
                "Python service missing field: data"
            );
        }
        return response.getData();
    }

    public boolean isHealthy() {
        try {
            ResponseEntity<Map<String, Object>> resp = restTemplate.getForEntity(
                pythonServiceUrl + "/health", (Class<Map<String, Object>>) (Class<?>) Map.class
            );
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("Python service health check failed: {}", e.getMessage());
            return false;
        }
    }

    private ConvertResponse callPythonService(MultipartFile file, String path) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartInputStreamFileResource(
                file.getInputStream(), file.getOriginalFilename()
            ));

            HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
            ResponseEntity<ConvertResponse> response = restTemplate.postForEntity(
                pythonServiceUrl + path, request, ConvertResponse.class
            );

            ConvertResponse result = response.getBody();
            if (result == null) {
                throw new PythonServiceException(
                    HttpStatus.BAD_GATEWAY.value(),
                    "Python service returned an empty response"
                );
            }

            if (!result.isSuccess()) {
                throw new PythonServiceException(
                    HttpStatus.BAD_GATEWAY.value(),
                    "Python service returned a non-success response"
                );
            }

            return result;

        } catch (HttpStatusCodeException e) {
            throw new PythonServiceException(
                e.getStatusCode().value(),
                extractDownstreamMessage(e),
                e
            );
        } catch (ResourceAccessException e) {
            throw new PythonServiceException(
                HttpStatus.GATEWAY_TIMEOUT.value(),
                "Python service is unavailable or timed out",
                e
            );
        } catch (IOException e) {
            throw new PythonServiceException(
                HttpStatus.BAD_REQUEST.value(),
                "Failed to read uploaded file",
                e
            );
        }
    }

    private String extractDownstreamMessage(HttpStatusCodeException e) {
        if (e.getStatusCode().is5xxServerError()) {
            return "Python conversion service failed";
        }

        String body = e.getResponseBodyAsString();
        if (body != null) {
            body = body.trim();
        }
        if (body == null || body.isEmpty()) {
            return "Python service returned " + e.getStatusCode().value();
        }

        try {
            JsonNode payload = objectMapper.readTree(body);
            if (payload.hasNonNull("detail")) {
                return payload.get("detail").asText();
            }
            if (payload.hasNonNull("message")) {
                return payload.get("message").asText();
            }
        } catch (IOException ignored) {
            // Fall back to the raw body for 4xx responses that are already user-facing.
        }

        return body;
    }
}
