# Service down (port closed)
Keywords: closed, refused, connection refused, service down, not listening, stopped, crashed

## Symptoms
- "Connection refused" errors
- App was working, then suddenly stopped

## Checks
1. ping_host the server. REACHABLE means the host is up.
2. check_port on the app port. CLOSED means nothing is listening.
3. parse_logs for crash, error, or out-of-memory messages.

## Likely causes
- Application service stopped or crashed
- Service failed to start after a reboot or patch

## Fix
- Restart the service and confirm the port shows OPEN
- Check logs for the crash reason before closing the ticket

## Escalate to
Application / Server team, priority P2