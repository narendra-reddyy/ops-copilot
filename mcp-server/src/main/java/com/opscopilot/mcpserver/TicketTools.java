package com.opscopilot.mcpserver;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

@Service
public class TicketTools {

    private static final List<String> PRIORITIES =
            List.of("1 - Critical", "2 - High", "3 - Moderate", "4 - Low");
    private static final List<String> CATEGORIES =
            List.of("Network", "DNS", "Server", "Storage", "Security", "Application");

    @Tool(description = "Draft an incident ticket. Call this LAST, after the diagnostic tools. "
            + "It does NOT file or save anything: it returns a draft for a human to review, "
            + "edit and save. Leave affected_users or reported_by empty unless the incident "
            + "text states them. Never guess.")
    public Map<String, Object> create_ticket(
            @ToolParam(description = "Short title under 80 characters, e.g. 'EHR app unreachable from floor 3 (port 443 timeout)'") String title,
            @ToolParam(description = "One of: 1 - Critical, 2 - High, 3 - Moderate, 4 - Low") String priority,
            @ToolParam(description = "One of: Network, DNS, Server, Storage, Security, Application") String category,
            @ToolParam(description = "Team to assign, e.g. Network Operations") String assignment_group,
            @ToolParam(description = "What the user reported, in plain English") String what_happened,
            @ToolParam(description = "Each check run and its result, one item per check, e.g. 'check_port 10.20.4.15:443 -> TIMED_OUT'") List<String> checks_run,
            @ToolParam(description = "Most likely cause, based only on the evidence") String likely_cause,
            @ToolParam(description = "Recommended next steps or fix") String recommended_fix,
            @ToolParam(description = "How many or which users are affected, only if stated", required = false) String affected_users,
            @ToolParam(description = "Who reported the incident, only if stated", required = false) String reported_by) {

        List<String> missing = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        if (blank(title)) missing.add("title");
        else if (title.length() > 80) warnings.add("title is longer than 80 characters");
        if (!PRIORITIES.contains(priority)) warnings.add("priority must be one of " + PRIORITIES);
        if (!CATEGORIES.contains(category)) warnings.add("category must be one of " + CATEGORIES);
        if (blank(assignment_group)) missing.add("assignment_group");
        if (blank(what_happened)) missing.add("what_happened");
        if (checks_run == null || checks_run.isEmpty()) missing.add("checks_run");
        if (blank(likely_cause)) missing.add("likely_cause");
        if (blank(recommended_fix)) missing.add("recommended_fix");
        if (blank(affected_users)) missing.add("affected_users");
        if (blank(reported_by)) missing.add("reported_by");

        Map<String, Object> ticket = new LinkedHashMap<>();
        ticket.put("status", "DRAFT");
        ticket.put("title", clean(title));
        ticket.put("priority", clean(priority));
        ticket.put("category", clean(category));
        ticket.put("assignment_group", clean(assignment_group));
        ticket.put("what_happened", clean(what_happened));
        ticket.put("checks_run", checks_run == null ? List.of() : checks_run);
        ticket.put("likely_cause", clean(likely_cause));
        ticket.put("recommended_fix", clean(recommended_fix));
        ticket.put("affected_users", clean(affected_users));
        ticket.put("reported_by", clean(reported_by));
        ticket.put("missing_fields", missing);
        ticket.put("warnings", warnings);
        ticket.put("drafted_at", ZonedDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        return ticket;
    }

    private static boolean blank(String s) {
        return s == null || s.isBlank();
    }

    private static String clean(String s) {
        return blank(s) ? null : s.trim();
    }
}