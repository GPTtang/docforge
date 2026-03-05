package com.docforge.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class ConvertResponse {
    private String filename;
    private String markdown;
    private Object data;       // JSON 模式用
    private String status;
    private String message;

    public boolean isSuccess() {
        return "success".equals(status);
    }
}
