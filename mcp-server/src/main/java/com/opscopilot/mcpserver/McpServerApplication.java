package com.opscopilot.mcpserver;

import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class McpServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(McpServerApplication.class, args);
    }

   
    @Bean
    public ToolCallbackProvider opsTools(NetworkTools networkTools,
                                         KnowledgeTools knowledgeTools,
                                         LogTools logTools) {
        return MethodToolCallbackProvider.builder()
                .toolObjects(networkTools, knowledgeTools, logTools)
                .build();
    }
}