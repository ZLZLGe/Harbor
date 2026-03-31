API Reference: Web Server Log Intrusion Analysis

Combined Log Format (Apache/Nginx)

"   "" """>   [] "  "   "" ""

Python re Module - Log Parsing

\S+) (?P\S+) (?P[^"]*)" '
r'(?P\d+) (?P\S+) "(?P[^"]*)" "(?P[^"]*)"'
)
match = pattern.match(line)
data = match.groupdict()">import re
pattern = re.compile(
r'(?P\S+) \S+ \S+ \[(?P[^\]]+)\] '
r'"(?P\S+) (?P\S+) (?P[^"]*)" '
r'(?P\d+) (?P\S+) "(?P[^"]*)" "(?P[^"]*)"'
)
match = pattern.match(line)
data = match.groupdict()

GeoIP2 Python Library

import geoip2.database
reader = geoip2.database.Reader("GeoLite2-City.mmdb")
response = reader.city("8.8.8.8")
response.country.name       # "United States"
response.city.name           # "Mountain View"
response.location.latitude   # 37.386
response.location.longitude  # -122.0838
reader.close()

Attack Signature Categories

Type
Example Pattern
Severity

SQLi
UNION SELECT, OR 1=1, SLEEP()
Critical

LFI
../../etc/passwd, php://filter
High

XSS