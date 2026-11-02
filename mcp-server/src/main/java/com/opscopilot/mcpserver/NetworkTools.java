package com.opscopilot.mcpserver;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.util.Arrays;
import java.util.stream.Collectors;

@Service
public class NetworkTools {

    // Only letters, digits, dots and hyphens: blocks command injection
    private static final Pattern SAFE_HOST = Pattern.compile("^[a-zA-Z0-9.-]{1,253}$");
    private static final boolean WINDOWS =
            System.getProperty("os.name").toLowerCase().contains("win");

    @Tool(description = "Ping a host to check if it is reachable on the network. "
            + "Returns reachability, packet loss and latency. Read-only.")
    public String ping_host(@ToolParam(description = "Hostname or IP address, e.g. github.com") String host) {
        if (host == null || !SAFE_HOST.matcher(host).matches()) {
            return "ERROR: invalid host name";
        }
        try {
            ProcessBuilder pb = WINDOWS
                    ? new ProcessBuilder("ping", "-n", "3", host)
                    : new ProcessBuilder("ping", "-c", "3", host);
            pb.redirectErrorStream(true);
            Process p = pb.start();

            StringBuilder out = new StringBuilder();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line;
                while ((line = r.readLine()) != null) {
                    if (!line.isBlank()) out.append(line.trim()).append("\n");
                }
            }
            if (!p.waitFor(15, TimeUnit.SECONDS)) {
                p.destroyForcibly();
                return "UNREACHABLE: ping timed out after 15 seconds";
            }
            String status = p.exitValue() == 0 ? "REACHABLE" : "UNREACHABLE";
            return status + "\n" + out;
        } catch (Exception e) {
            return "ERROR: " + e.getMessage();
        }
    }

        @Tool(description = "Resolve a hostname to its IP addresses using DNS. "
            + "Use this to check whether name resolution works. Read-only.")
    public String dns_lookup(@ToolParam(description = "Hostname to resolve, e.g. github.com") String host) {
        if (host == null || !SAFE_HOST.matcher(host).matches()) {
            return "ERROR: invalid host name";
        }
        try {
            long start = System.currentTimeMillis();
            InetAddress[] addresses = InetAddress.getAllByName(host);
            long ms = System.currentTimeMillis() - start;
            String ips = Arrays.stream(addresses)
                    .map(InetAddress::getHostAddress)
                    .collect(Collectors.joining(", "));
            return "RESOLVED in " + ms + " ms: " + host + " -> " + ips;
        } catch (UnknownHostException e) {
            return "DNS_FAILURE: " + host + " could not be resolved (no such host or DNS server unreachable)";
        } catch (Exception e) {
            return "ERROR: " + e.getMessage();
        }
    }

    @Tool(description = "Check whether a TCP port is open on a host, e.g. 443 for HTTPS, "
            + "22 for SSH, 3306 for MySQL. Returns OPEN, CLOSED or TIMED_OUT. Read-only.")
    public String check_port(
            @ToolParam(description = "Hostname or IP address") String host,
            @ToolParam(description = "TCP port number, 1-65535") int port) {
        if (host == null || !SAFE_HOST.matcher(host).matches()) {
            return "ERROR: invalid host name";
        }
        if (port < 1 || port > 65535) {
            return "ERROR: port must be between 1 and 65535";
        }
        int timeoutMs = 3000;
        long start = System.currentTimeMillis();
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), timeoutMs);
            long ms = System.currentTimeMillis() - start;
            return "OPEN: " + host + ":" + port + " accepted a connection in " + ms + " ms";
        } catch (SocketTimeoutException e) {
            return "TIMED_OUT: no response from " + host + ":" + port + " after " + timeoutMs
                    + " ms (often a firewall silently dropping traffic)";
        } catch (UnknownHostException e) {
            return "DNS_FAILURE: " + host + " could not be resolved";
        } catch (java.net.ConnectException e) {
            return "CLOSED: " + host + ":" + port + " refused the connection (host is up, nothing listening)";
        } catch (Exception e) {
            return "ERROR: " + e.getMessage();
        }
    }
}