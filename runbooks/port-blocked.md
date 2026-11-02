# Port blocked or timing out
Keywords: port, timeout, timed out, firewall, 443, https, load balancer, host reachable

## Symptoms
- App won't load, but the server answers ping
- Browser spins, then times out

## Checks
1. ping_host the server. REACHABLE means the network path is fine.
2. dns_lookup the name. RESOLVED rules out DNS.
3. check_port on the app port (usually 443). TIMED_OUT points to a firewall.

## Likely causes
- New or changed firewall rule dropping the port
- Load balancer health check failing, pool marked down
- Security group change (cloud)

## Fix
- Review firewall changes for that IP and port in the last 24 hours
- Check load balancer pool health

## Escalate to
Network Operations, priority P2