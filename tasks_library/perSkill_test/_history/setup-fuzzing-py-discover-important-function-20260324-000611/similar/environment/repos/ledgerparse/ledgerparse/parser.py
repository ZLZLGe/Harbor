import csv
import io


def parse_invoice_text(raw: str) -> list[dict[str, str]]:
    """Parse supplier invoice rows separated by pipes."""
    records = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        vendor, invoice_id, total = line.split("|")
        records.append({"vendor": vendor, "invoice_id": invoice_id, "total": total})
    return records


def decode_ledger_csv(raw: str) -> list[dict[str, str]]:
    """Decode CSV exports into dictionaries keyed by the header row."""
    reader = csv.DictReader(io.StringIO(raw))
    return [dict(row) for row in reader]


def summarize_totals(records: list[dict[str, str]]) -> float:
    total = 0.0
    for record in records:
        total += float(record["total"])
    return total
