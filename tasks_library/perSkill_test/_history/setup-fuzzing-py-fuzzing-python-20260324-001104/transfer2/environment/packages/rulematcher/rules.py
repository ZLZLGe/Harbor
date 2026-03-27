import re


RULE_RE = re.compile(
    r"^(allow|deny)\s+(tcp|udp)\s+([A-Z]{2,8})\s+([a-z0-9_.-]{1,24})\s+(src|dst)=(\d{1,5})$"
)


def evaluate_rule_line(text: str) -> dict[str, object]:
    text = text.strip()
    if not text:
        return {"status": "empty"}

    match = RULE_RE.fullmatch(text)
    if not match:
        return {"status": "invalid", "length": len(text)}

    action, protocol, code, host, direction, port = match.groups()
    port_num = int(port)
    if host.startswith("internal-") and direction == "dst" and port_num == 443:
        return {"status": "internal-tls", "action": action, "code": code}
    if host.endswith(".lab") and protocol == "udp" and action == "deny":
        return {"status": "blocked-lab", "code": code}
    return {"status": "ok", "port": port_num}
