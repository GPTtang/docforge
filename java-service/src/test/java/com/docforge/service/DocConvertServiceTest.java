package com.docforge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

class DocConvertServiceTest {

    private RestTemplate restTemplate;
    private MockRestServiceServer server;
    private DocConvertService service;

    @BeforeEach
    void setUp() {
        restTemplate = new RestTemplate();
        server = MockRestServiceServer.createServer(restTemplate);
        service = new DocConvertService(restTemplate, new ObjectMapper());
        ReflectionTestUtils.setField(service, "pythonServiceUrl", "http://python-service");
    }

    @Test
    void convertToJsonUsesTypedConvertResponse() {
        server.expect(requestTo("http://python-service/convert/json"))
            .andExpect(method(HttpMethod.POST))
            .andRespond(withStatus(HttpStatus.OK)
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                    {
                      "filename": "sample.pdf",
                      "status": "success",
                      "data": {
                        "engine": "opendataloader",
                        "pages": 2
                      }
                    }
                    """));

        JsonNode payload = service.convertToJson(
            new MockMultipartFile("file", "sample.pdf", "application/pdf", "pdf".getBytes())
        );

        assertThat(payload.get("engine").asText()).isEqualTo("opendataloader");
        assertThat(payload.get("pages").asInt()).isEqualTo(2);
        server.verify();
    }

    @Test
    void convertToMarkdownSanitizesDownstream5xxErrors() {
        server.expect(requestTo("http://python-service/convert/markdown"))
            .andExpect(method(HttpMethod.POST))
            .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                .contentType(MediaType.APPLICATION_JSON)
                .body("""
                    {"detail":"/tmp/docforge/secret-path traceback ..."}
                    """));

        assertThatThrownBy(() -> service.convertToMarkdown(
            new MockMultipartFile("file", "sample.pdf", "application/pdf", "pdf".getBytes())
        ))
            .isInstanceOf(PythonServiceException.class)
            .hasMessage("Python conversion service failed");

        server.verify();
    }
}
