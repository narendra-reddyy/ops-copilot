# Host unreachable
Keywords: unreachable, down, offline, no reply, request timed out, ping fails, 100% loss

## Symptoms
- Server doesn't answer ping
- Nothing on that server works

## Checks
1. dns_lookup the name. RESOLVED means DNS is fine.
2. ping_host the server. UNREACHABLE with 100% loss confirms it.
3. ping_host another server on the same subnet to tell a single host from a network problem.

## Likely causes
- Server powered off, crashed, or stuck rebooting
- Network cable, switch port, or VLAN issue
- Host firewall blocking ICMP (check a port before concluding it's down)

## Fix
- Check the server console or iLO/iDRAC
- Check the switch port status

## Escalate to
Data Center / Server team, priority P1 if production