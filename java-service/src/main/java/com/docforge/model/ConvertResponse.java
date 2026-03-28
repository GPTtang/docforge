package com.docforge.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class ConvertResponse {
    private String filename;
    private String markdown;
    private JsonNode data;
    private String status;
    private String message;

    public boolean isSuccess() {
        return "success".equals(status);
    }
}
