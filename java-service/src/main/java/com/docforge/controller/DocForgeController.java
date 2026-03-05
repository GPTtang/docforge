package com.docforge.controller;

import com.docforge.service.DocConvertService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/convert")
@Slf4j
public class DocForgeController {

    @Autowired
    private DocConvertService convertService;

    @PostMapping("/markdown")
    public ResponseEntity<?> toMarkdown(@RequestParam("file") MultipartFile file) {
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

    @PostMapping("/json")
    public ResponseEntity<?> toJson(@RequestParam("file") MultipartFile file) {
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
