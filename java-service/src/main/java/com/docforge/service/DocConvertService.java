package com.docforge.service;

import com.docforge.util.MultipartInputStreamFileResource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;

@Service
@Slf4j
public class DocConvertService {

    @Value("${docforge.python.service-url}")
    private String pythonServiceUrl;

    @Autowired
    private RestTemplate restTemplate;

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
            log.warn("Python service 健康检查失败: {}", e.getMessage());
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
            if (result == null || !"success".equals(result.get("status"))) {
                throw new RuntimeException("Python 服务返回错误: " +
                    (result != null ? result.get("message") : "无响应"));
            }
            return (T) result.get(field);

        } catch (IOException e) {
            throw new RuntimeException("文件读取失败: " + e.getMessage(), e);
        }
    }
}
