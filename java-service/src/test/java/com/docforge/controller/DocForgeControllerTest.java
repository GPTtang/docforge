package com.docforge.controller;

import com.docforge.service.DocConvertService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DocForgeController.class)
class DocForgeControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private DocConvertService convertService;

    @Test
    void healthReturnsJavaAndPythonStatus() throws Exception {
        when(convertService.isHealthy()).thenReturn(true);

        mockMvc.perform(get("/api/convert/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.java").value("ok"))
            .andExpect(jsonPath("$.python").value("ok"));
    }
}
