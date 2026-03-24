import csv
import os


EXPECTED_HEADERS = [
    "Artifact",
    "Package",
    "Installed_Version",
    "Advisory_ID",
    "Severity",
    "CVSS_Score",
    "Score_Source",
    "Fixed_Version",
    "Title",
    "Reference_URL",
]

EXPECTED_ROWS = {
    (
        "jobs/worker/package-lock.json",
        "minimist",
        "1.2.2",
        "CVE-2021-44906",
    ): {
        "Artifact": "jobs/worker/package-lock.json",
        "Package": "minimist",
        "Installed_Version": "1.2.2",
        "Advisory_ID": "CVE-2021-44906",
        "Severity": "CRITICAL",
        "CVSS_Score": "9.8",
        "Score_Source": "NVD",
        "Fixed_Version": "1.2.6",
        "Title": "minimist susceptible to prototype pollution",
        "Reference_URL": "https://nvd.nist.gov/vuln/detail/CVE-2021-44906",
    },
    (
        "jobs/worker/package-lock.json",
        "xmldom",
        "0.6.0",
        "CVE-2023-28155",
    ): {
        "Artifact": "jobs/worker/package-lock.json",
        "Package": "xmldom",
        "Installed_Version": "0.6.0",
        "Advisory_ID": "CVE-2023-28155",
        "Severity": "HIGH",
        "CVSS_Score": "8.0",
        "Score_Source": "RedHat",
        "Fixed_Version": "N/A",
        "Title": "xmldom accepts multiple root nodes in crafted XML",
        "Reference_URL": "https://access.redhat.com/security/cve/CVE-2023-28155",
    },
    (
        "services/api/package-lock.json",
        "cookie",
        "0.4.1",
        "GHSA-pxg6-pf52-xh8x",
    ): {
        "Artifact": "services/api/package-lock.json",
        "Package": "cookie",
        "Installed_Version": "0.4.1",
        "Advisory_ID": "GHSA-pxg6-pf52-xh8x",
        "Severity": "HIGH",
        "CVSS_Score": "N/A",
        "Score_Source": "N/A",
        "Fixed_Version": "0.7.0",
        "Title": "cookie accepts out-of-range max-age values",
        "Reference_URL": "https://github.com/advisories/GHSA-pxg6-pf52-xh8x",
    },
    (
        "services/api/package-lock.json",
        "json5",
        "1.0.1",
        "CVE-2024-12345",
    ): {
        "Artifact": "services/api/package-lock.json",
        "Package": "json5",
        "Installed_Version": "1.0.1",
        "Advisory_ID": "CVE-2024-12345",
        "Severity": "HIGH",
        "CVSS_Score": "7.1",
        "Score_Source": "NVD",
        "Fixed_Version": "1.0.2",
        "Title": "json5 prototype pollution in parse path",
        "Reference_URL": "https://advisories.example.internal/CVE-2024-12345",
    },
    (
        "services/web/package-lock.json",
        "ws",
        "7.5.7",
        "GHSA-3h5v-q93c-6h6q",
    ): {
        "Artifact": "services/web/package-lock.json",
        "Package": "ws",
        "Installed_Version": "7.5.7",
        "Advisory_ID": "GHSA-3h5v-q93c-6h6q",
        "Severity": "CRITICAL",
        "CVSS_Score": "9.8",
        "Score_Source": "GHSA",
        "Fixed_Version": "7.5.10",
        "Title": "ws vulnerable to request smuggling in header handling",
        "Reference_URL": "https://github.com/advisories/GHSA-3h5v-q93c-6h6q",
    },
}


def get_csv_path():
    candidates = [
        os.environ.get("AUDIT_CSV_PATH"),
        "/root/advisory_priority_audit.csv",
        "advisory_priority_audit.csv",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("advisory_priority_audit.csv not found")


def read_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


def normalize(rows):
    normalized = {}
    for row in rows:
        item = {key: (value or "").strip() for key, value in row.items()}
        if not item["Fixed_Version"]:
            item["Fixed_Version"] = "N/A"
        key = (
            item["Artifact"],
            item["Package"],
            item["Installed_Version"],
            item["Advisory_ID"],
        )
        normalized[key] = item
    return normalized


def main():
    path = get_csv_path()
    headers, rows = read_rows(path)

    assert headers == EXPECTED_HEADERS, f"CSV headers mismatch: {headers}"
    assert rows, "CSV must contain vulnerability rows"

    for row in rows:
        severity = row["Severity"].strip()
        assert severity in {"HIGH", "CRITICAL"}, f"unexpected severity: {severity}"

    actual = normalize(rows)
    assert actual == EXPECTED_ROWS, "CSV content does not match expected advisory export"


if __name__ == "__main__":
    main()
