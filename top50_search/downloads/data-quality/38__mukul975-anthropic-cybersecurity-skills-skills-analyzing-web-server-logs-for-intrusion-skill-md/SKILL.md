name
analyzing-web-server-logs-for-intrusion

description
Parse Apache and Nginx access logs to detect SQL injection attempts, local file inclusion, directory traversal, web scanner fingerprints, and brute-force patterns. Uses regex-based pattern matching against OWASP attack signatures, GeoIP enrichment for source attribution, and statistical anomaly detection for request frequency and response size outliers.

domain
cybersecurity

subdomain
security-operations

tags

analyzing

web

server

logs

version
1.0

author
mahipal

license
Apache-2.0

Analyzing Web Server Logs for Intrusion

When to Use

When investigating security incidents that require analyzing web server logs for intrusion

When building detection rules or threat hunting queries for this domain

When SOC analysts need structured procedures for this analysis type

When validating security monitoring coverage for related attack techniques

Prerequisites

Familiarity with security operations concepts and tools

Access to a test or lab environment for safe execution

Python 3.8+ with required dependencies installed

Appropriate authorization for any testing activities

Instructions

Install dependencies: pip install geoip2 user-agents

Collect web server access logs in Combined Log Format (Apache) or Nginx default format.

Parse each log entry extracting: IP, timestamp, method, URI, status code, response size, user-agent, referer.

Apply detection rules:

SQL injection: UNION SELECT, OR 1=1, ' OR ', hex encoding patterns

LFI/Path traversal: ../, /etc/passwd, /proc/self, php://filter

XSS: