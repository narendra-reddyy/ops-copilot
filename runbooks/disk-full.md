# Disk full
Keywords: disk, full, no space, storage, volume, 100%, slow, write failed

## Symptoms
- App errors when saving or uploading
- System is slow or services fail to start

## Checks
1. parse_logs for "no space left on device" or "disk full".
2. Confirm the server is reachable with ping_host.

## Likely causes
- Log files grew without rotation
- Backups or temp files filling the volume

## Fix
- Clear old logs and temp files, then set up log rotation
- Extend the volume if growth is expected

## Escalate to
Server / Storage team, priority P3 (P2 if a service is down)