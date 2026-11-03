package com.opscopilot.mcpserver;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class LogTools {

    private static final int MAX_LINES = 20;
    private final Path logDir;

    public LogTools(@Value("${opscopilot.logs-dir:../logs}") String dir) {
        this.logDir = Paths.get(dir).toAbsolutePath().normalize();
    }

    @Tool(description = "Search a log file for lines containing a keyword, e.g. 'error', "
            + "'refused', 'no space', 'failed password'. Case-insensitive. Returns the match "
            + "count and the most recent matching lines. Leave file empty to list available "
            + "log files. Read-only.")
    public String parse_logs(
            @ToolParam(description = "Log file name, e.g. app.log. Empty to list files", required = false) String file,
            @ToolParam(description = "Keyword or phrase to search for", required = false) String keyword) {

        // No file given: list what is available
        if (file == null || file.isBlank()) {
            try (Stream<Path> files = Files.list(logDir)) {
                String names = files.filter(Files::isRegularFile)
                        .map(p -> p.getFileName().toString())
                        .collect(Collectors.joining(", "));
                return names.isEmpty() ? "NO_LOG_FILES found" : "AVAILABLE LOG FILES: " + names;
            } catch (IOException e) {
                return "ERROR: cannot read logs folder: " + e.getMessage();
            }
        }

        // Safety: the file must stay inside the logs folder (blocks ../../ tricks)
        Path path = logDir.resolve(file).normalize();
        if (!path.startsWith(logDir) || !Files.isRegularFile(path)) {
            return "ERROR: log file not found: " + file;
        }

        try {
            List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
            String kw = keyword == null ? "" : keyword.toLowerCase().trim();
            List<String> matches = kw.isEmpty()
                    ? lines
                    : lines.stream().filter(l -> l.toLowerCase().contains(kw)).toList();

            if (matches.isEmpty()) {
                return "NO_MATCHES: '" + keyword + "' not found in " + file
                        + " (" + lines.size() + " lines searched)";
            }
            List<String> recent = matches.subList(Math.max(0, matches.size() - MAX_LINES), matches.size());
            return "FOUND " + matches.size() + " matching line(s) in " + file
                    + (matches.size() > MAX_LINES ? " (showing last " + MAX_LINES + ")" : "")
                    + ":\n" + String.join("\n", recent);
        } catch (IOException e) {
            return "ERROR: cannot read " + file + ": " + e.getMessage();
        }
    }
}