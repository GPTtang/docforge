package com.docforge.service;

import com.docforge.util.MultipartInputStreamFileResource;
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

    public DocConvertService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public String convertToMarkdown(MultipartFile file) {
        return callPythonService(file, "/convert/markdown", "markdown");
    }

    public Map<String, Object> convertToJson(MultipartFile file) {
        return callPythonService(file, "/convert/json", "data");
    }

    public boolean isHealthy() {
        try {
            ResponseEntity<Map> resp = restTemplate.getForEntity(
                pythonServiceUrl + "/health", Map.class
            );
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("Python service health check failed: {}", e.getMessage());
            return false;
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T callPythonService(MultipartFile file, String path, String field) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new MultipartInputStreamFileResource(
                file.getInputStream(), file.getOriginalFilename()
            ));

            HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.postForEntity(
                pythonServiceUrl + path, request, Map.class
            );

            Map<String, Object> result = response.getBody();
            if (result == null) {
                throw new PythonServiceException(
                    HttpStatus.BAD_GATEWAY.value(),
                    "Python service returned an empty response"
                );
            }

            if (!"success".equals(result.get("status"))) {
                throw new PythonServiceException(
                    HttpStatus.BAD_GATEWAY.value(),
                    "Python service error: " + result.getOrDefault("message", "unknown error")
                );
            }

            Object payload = result.get(field);
            if (payload == null) {
                throw new PythonServiceException(
                    HttpStatus.BAD_GATEWAY.value(),
                    "Python service missing field: " + field
                );
            }

            return (T) payload;

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
        String body = e.getResponseBodyAsString();
        if (body != null) {
            body = body.trim();
        }
        if (body != null && !body.isEmpty()) {
            return body;
        }
        return "Python service returned " + e.getStatusCode().value();
    }
}
