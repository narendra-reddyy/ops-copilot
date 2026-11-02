package com.opscopilot.mcpserver;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class KnowledgeTools {

    private final Path runbookDir;

    public KnowledgeTools(@Value("${opscopilot.runbooks-dir:../runbooks}") String dir) {
        this.runbookDir = Paths.get(dir).toAbsolutePath().normalize();
    }

    private record Hit(String file, String text, int score) {}

    @Tool(description = "Search the team's troubleshooting runbooks using keywords or symptoms, "
            + "e.g. 'port 443 timeout host reachable'. Returns the best matching runbook with "
            + "checks, likely causes, fix and who to escalate to. Read-only.")
    public String search_runbook(
            @ToolParam(description = "Keywords or symptoms describing the problem") String query) {
        if (query == null || query.isBlank()) {
            return "ERROR: query is empty";
        }
        List<String> terms = Arrays.stream(query.toLowerCase().split("[^a-z0-9]+"))
                .filter(t -> t.length() > 1)
                .distinct()
                .toList();

        List<Hit> hits = new ArrayList<>();
        try (Stream<Path> files = Files.list(runbookDir)) {
            for (Path p : files.filter(f -> f.toString().endsWith(".md")).toList()) {
                String text = Files.readString(p);
                String lower = text.toLowerCase();
                String keywords = lower.lines()
                        .filter(l -> l.startsWith("keywords:"))
                        .findFirst().orElse("");
                int score = 0;
                for (String t : terms) {
                    if (keywords.contains(t)) score += 3;   // keyword line counts more
                    if (lower.contains(t)) score += 1;
                }
                if (score > 0) hits.add(new Hit(p.getFileName().toString(), text, score));
            }
        } catch (IOException e) {
            return "ERROR: cannot read runbooks folder " + runbookDir + ": " + e.getMessage();
        }

        if (hits.isEmpty()) {
            return "NO_MATCH: no runbook matches '" + query + "'. Diagnose from tool results only.";
        }
        hits.sort(Comparator.comparingInt(Hit::score).reversed());
        Hit best = hits.get(0);
        String others = hits.stream().skip(1).limit(2)
                .map(h -> h.file() + " (score " + h.score() + ")")
                .collect(Collectors.joining(", "));

        return "BEST MATCH: " + best.file() + " (score " + best.score() + ")\n\n"
                + best.text()
                + (others.isEmpty() ? "" : "\n\nOTHER POSSIBLE MATCHES: " + others);
    }
}