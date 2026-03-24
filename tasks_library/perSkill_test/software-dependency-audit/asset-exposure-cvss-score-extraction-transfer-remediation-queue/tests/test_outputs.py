import csv
import os


EXPECTED_HEADERS = [
    "Queue_Position",
    "Asset_ID",
    "Business_Service",
    "Environment",
    "Vulnerability_ID",
    "Package",
    "Installed_Version",
    "Selected_CVSS",
    "Score_Source",
    "Exposure_Points",
    "Priority_Score",
    "Remediation_Band",
    "Patch_Window",
    "Fixed_Version",
    "Reference_URL",
]

EXPECTED_ROWS = [
    {
        "Queue_Position": "1",
        "Asset_ID": "edge-gw-01",
        "Business_Service": "Partner API Gateway",
        "Environment": "production",
        "Vulnerability_ID": "CVE-2026-41001",
        "Package": "gatewayd",
        "Installed_Version": "4.2.1",
        "Selected_CVSS": "8.4",
        "Score_Source": "NVD",
        "Exposure_Points": "10",
        "Priority_Score": "84.0",
        "Remediation_Band": "P1",
        "Patch_Window": "Sun 01:00-03:00 UTC",
        "Fixed_Version": "4.2.4",
        "Reference_URL": "https://nvd.nist.gov/vuln/detail/CVE-2026-41001",
    },
    {
        "Queue_Position": "2",
        "Asset_ID": "edge-gw-01",
        "Business_Service": "Partner API Gateway",
        "Environment": "production",
        "Vulnerability_ID": "CVE-2026-41015",
        "Package": "metrics-agent",
        "Installed_Version": "3.1.8",
        "Selected_CVSS": "7.5",
        "Score_Source": "GHSA",
        "Exposure_Points": "10",
        "Priority_Score": "75.0",
        "Remediation_Band": "P1",
        "Patch_Window": "Sun 01:00-03:00 UTC",
        "Fixed_Version": "3.2.0",
        "Reference_URL": "https://access.redhat.com/security/cve/CVE-2026-41015",
    },
    {
        "Queue_Position": "3",
        "Asset_ID": "erp-batch-02",
        "Business_Service": "Finance Batch Processor",
        "Environment": "production",
        "Vulnerability_ID": "GHSA-qq44-v6v8-9h6m",
        "Package": "ledger-sync",
        "Installed_Version": "2.7.0",
        "Selected_CVSS": "8.6",
        "Score_Source": "GHSA",
        "Exposure_Points": "7",
        "Priority_Score": "60.2",
        "Remediation_Band": "P1",
        "Patch_Window": "Sat 18:00-20:00 UTC",
        "Fixed_Version": "2.7.3",
        "Reference_URL": "https://github.com/advisories/GHSA-qq44-v6v8-9h6m",
    },
    {
        "Queue_Position": "4",
        "Asset_ID": "store-kiosk-17",
        "Business_Service": "Retail Kiosk Fleet",
        "Environment": "store-edge",
        "Vulnerability_ID": "CVE-2026-41007",
        "Package": "receipt-renderer",
        "Installed_Version": "1.9.4",
        "Selected_CVSS": "7.2",
        "Score_Source": "RedHat",
        "Exposure_Points": "7",
        "Priority_Score": "50.4",
        "Remediation_Band": "P2",
        "Patch_Window": "Mon 02:00-04:00 UTC",
        "Fixed_Version": "N/A",
        "Reference_URL": "https://access.redhat.com/security/cve/CVE-2026-41007",
    },
    {
        "Queue_Position": "5",
        "Asset_ID": "hr-portal-03",
        "Business_Service": "HR Self-Service Portal",
        "Environment": "production",
        "Vulnerability_ID": "CVE-2026-41011",
        "Package": "session-kit",
        "Installed_Version": "5.4.0",
        "Selected_CVSS": "6.9",
        "Score_Source": "NVD",
        "Exposure_Points": "7",
        "Priority_Score": "48.3",
        "Remediation_Band": "P2",
        "Patch_Window": "Wed 00:00-02:00 UTC",
        "Fixed_Version": "5.4.2",
        "Reference_URL": "https://nvd.nist.gov/vuln/detail/CVE-2026-41011",
    },
    {
        "Queue_Position": "6",
        "Asset_ID": "lab-report-01",
        "Business_Service": "Lab Reporting",
        "Environment": "staging",
        "Vulnerability_ID": "GHSA-z8rj-fhhm-x5cp",
        "Package": "report-export",
        "Installed_Version": "0.18.2",
        "Selected_CVSS": "N/A",
        "Score_Source": "N/A",
        "Exposure_Points": "3",
        "Priority_Score": "0.0",
        "Remediation_Band": "P3",
        "Patch_Window": "Fri 03:00-05:00 UTC",
        "Fixed_Version": "0.18.5",
        "Reference_URL": "https://github.com/advisories/GHSA-z8rj-fhhm-x5cp",
    },
]


def get_output_path():
    candidates = [
        os.environ.get("REMEDIATION_QUEUE_PATH"),
        "/root/remediation_queue.tsv",
        "remediation_queue.tsv",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("remediation_queue.tsv not found")


def read_tsv(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        headers = reader.fieldnames
        rows = list(reader)
    return headers, rows


def main():
    path = get_output_path()
    headers, rows = read_tsv(path)

    assert headers == EXPECTED_HEADERS, f"TSV headers mismatch: {headers}"
    assert rows == EXPECTED_ROWS, "TSV content does not match expected remediation queue"


if __name__ == "__main__":
    main()
