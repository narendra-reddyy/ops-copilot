# DNS failure
Keywords: dns, resolve, name resolution, could not find host, nxdomain, unknown host

## Symptoms
- Users get "server not found" or "could not find host"
- Ping by name fails, but ping by IP works

## Checks
1. dns_lookup the hostname. DNS_FAILURE confirms it.
2. ping_host the IP directly. If it replies, the server is fine and only DNS is broken.
3. dns_lookup a known good name like github.com to test the DNS server itself.

## Likely causes
- Missing or deleted DNS record
- Typo in the hostname
- DNS server down or unreachable

## Fix
- Recreate or correct the A record
- If all lookups fail, check the DNS server and the client's DNS settings

## Escalate to
DNS / Network team, priority P2 if many users are affected