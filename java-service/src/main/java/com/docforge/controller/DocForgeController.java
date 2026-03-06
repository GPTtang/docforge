package com.docforge.controller;

import com.docforge.service.DocConvertService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/convert")
@Slf4j
@Tag(name = "Document Conversion", description = "APIs for converting documents to Markdown or JSON")
public class DocForgeController {

    @Autowired
    private DocConvertService convertService;

    @Operation(summary = "Convert file to Markdown", description = "Uploads a document (PDF, Word, Excel, PowerPoint) and converts it to Markdown format")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Conversion successful"),
        @ApiResponse(responseCode = "400", description = "File is empty or unsupported format"),
        @ApiResponse(responseCode = "500", description = "Conversion failed")
    })
    @PostMapping(value = "/markdown", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> toMarkdown(
            @Parameter(description = "Document file to convert (PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT)", required = true)
            @RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(error("文件不能为空"));
        }
        try {
            String markdown = convertService.convertToMarkdown(file);
            return ResponseEntity.ok(Map.of(
                "filename", file.getOriginalFilename(),
                "markdown", markdown,
                "status", "success"
            ));
        } catch (Exception e) {
            log.error("Markdown 转换失败: {}", e.getMessage());
            return ResponseEntity.status(500).body(error(e.getMessage()));
        }
    }

    @Operation(summary = "Convert file to JSON", description = "Uploads a document (PDF, Word, Excel, PowerPoint) and converts it to structured JSON format")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Conversion successful"),
        @ApiResponse(responseCode = "400", description = "File is empty or unsupported format"),
        @ApiResponse(responseCode = "500", description = "Conversion failed")
    })
    @PostMapping(value = "/json", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<?> toJson(
            @Parameter(description = "Document file to convert (PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT)", required = true)
            @RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            return ResponseEntity.badRequest().body(error("文件不能为空"));
        }
        try {
            Map<String, Object> data = convertService.convertToJson(file);
            return ResponseEntity.ok(Map.of(
                "filename", file.getOriginalFilename(),
                "data", data,
                "status", "success"
            ));
        } catch (Exception e) {
            log.error("JSON 转换失败: {}", e.getMessage());
            return ResponseEntity.status(500).body(error(e.getMessage()));
        }
    }

    @Operation(summary = "Health check", description = "Checks the health status of both Java and Python services")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Health status returned")
    })
    @GetMapping("/health")
    public ResponseEntity<?> health() {
        boolean pythonOk = convertService.isHealthy();
        return ResponseEntity.ok(Map.of(
            "java", "ok",
            "python", pythonOk ? "ok" : "unavailable"
        ));
    }

    private Map<String, String> error(String msg) {
        return Map.of("status", "error", "message", msg);
    }
}