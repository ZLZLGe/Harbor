#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
INPUT_FILE="${TASK_ROOT}/mixed_identifiers.txt"
CACHE_DIR="${TASK_ROOT}/api_cache"
OUTPUT_FILE="${TASK_ROOT}/assembled_references.bib"

python3 - "$INPUT_FILE" "$CACHE_DIR" "$OUTPUT_FILE" <<'PY'
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


INPUT_FILE = Path(sys.argv[1])
CACHE_DIR = Path(sys.argv[2])
OUTPUT_FILE = Path(sys.argv[3])


@dataclass
class CitationRecord:
    source_type: str
    entry_type: str
    title: str
    authors: str
    year: str
    journal: str = ""
    booktitle: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    note: str = ""
    pmid: str = ""
    arxiv_id: str = ""


def read_identifiers(path: Path) -> list[str]:
    identifiers = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        identifiers.append(line)
    return identifiers


def sanitize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def identify_identifier(raw: str) -> tuple[str, str]:
    value = raw.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        if "doi.org" in host:
            return "doi", parsed.path.lstrip("/")
        if "pubmed.ncbi.nlm.nih.gov" in host:
            match = re.search(r"/(\d+)/?", parsed.path)
            if match:
                return "pmid", match.group(1)
        if "arxiv.org" in host:
            match = re.search(r"/abs/(\d{4}\.\d{4,5})(v\d+)?", parsed.path)
            if match:
                return "arxiv", match.group(1)
        raise ValueError(f"Unsupported URL identifier: {value}")

    if value.startswith("10."):
        return "doi", value

    if re.fullmatch(r"\d{7,9}", value):
        return "pmid", value

    if value.startswith("arXiv:"):
        value = value.split(":", 1)[1]

    match = re.fullmatch(r"(\d{4}\.\d{4,5})(v\d+)?", value)
    if match:
        return "arxiv", match.group(1)

    raise ValueError(f"Unsupported identifier: {raw}")


def cache_path(identifier_type: str, identifier: str) -> Path:
    extension = "json" if identifier_type == "doi" else "xml"
    return CACHE_DIR / f"{identifier_type}__{sanitize_identifier(identifier)}.{extension}"


def clean_text(value: str) -> str:
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_pages(pages: str) -> str:
    pages = clean_text(pages)
    if re.fullmatch(r"\d+-\d+", pages):
        return pages.replace("-", "--", 1)
    return pages


def format_crossref_authors(authors: list[dict]) -> str:
    formatted = []
    for author in authors:
        family = clean_text(author.get("family", ""))
        given = clean_text(author.get("given", ""))
        if family and given:
            formatted.append(f"{family}, {given}")
        elif family:
            formatted.append(family)
    return " and ".join(formatted)


def parse_crossref(path: Path) -> CitationRecord:
    message = json.loads(path.read_text(encoding="utf-8"))["message"]
    work_type = message.get("type", "")
    entry_type = "article"
    journal = ""
    booktitle = ""
    container_title = clean_text((message.get("container-title") or [""])[0])

    if work_type == "proceedings-article":
        entry_type = "inproceedings"
        booktitle = container_title
    else:
        journal = container_title

    date_parts = message.get("published-print", {}).get("date-parts", [[]])
    if not date_parts or not date_parts[0]:
        date_parts = message.get("published-online", {}).get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

    doi = clean_text(message.get("DOI", ""))
    return CitationRecord(
        source_type="doi",
        entry_type=entry_type,
        title=clean_text((message.get("title") or [""])[0]),
        authors=format_crossref_authors(message.get("author", [])),
        year=year,
        journal=journal,
        booktitle=booktitle,
        volume=clean_text(str(message.get("volume", ""))) if message.get("volume") else "",
        number=clean_text(str(message.get("issue", ""))) if message.get("issue") else "",
        pages=normalize_pages(message.get("page", "")),
        doi=doi,
        url=clean_text(message.get("URL", "")) or (f"https://doi.org/{doi}" if doi else ""),
    )


def format_pubmed_authors(author_nodes: list[ET.Element]) -> str:
    formatted = []
    for author in author_nodes:
        family = clean_text(author.findtext("LastName", default=""))
        given = clean_text(author.findtext("ForeName", default=""))
        if family and given:
            formatted.append(f"{family}, {given}")
        elif family:
            formatted.append(family)
    return " and ".join(formatted)


def parse_pubmed(path: Path) -> CitationRecord:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    article = root.find(".//Article")
    if article is None:
        raise ValueError(f"Missing Article element in {path}")

    journal = article.find("Journal")
    journal_title = clean_text(journal.findtext("Title", default="")) if journal is not None else ""
    year = ""
    volume = ""
    number = ""
    if journal is not None:
        journal_issue = journal.find("JournalIssue")
        if journal_issue is not None:
            year = clean_text(journal_issue.findtext("./PubDate/Year", default=""))
            volume = clean_text(journal_issue.findtext("Volume", default=""))
            number = clean_text(journal_issue.findtext("Issue", default=""))

    doi = ""
    for article_id in root.findall(".//ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            doi = clean_text(article_id.text or "")
            break

    pmid = clean_text(root.findtext(".//PMID", default=""))
    return CitationRecord(
        source_type="pmid",
        entry_type="article",
        title=clean_text(article.findtext("ArticleTitle", default="")),
        authors=format_pubmed_authors(article.findall(".//Author")),
        year=year,
        journal=journal_title,
        volume=volume,
        number=number,
        pages=normalize_pages(article.findtext("./Pagination/MedlinePgn", default="")),
        doi=doi,
        url=f"https://doi.org/{doi}" if doi else "",
        note=f"PMID: {pmid}" if pmid else "",
        pmid=pmid,
    )


def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def parse_arxiv(path: Path, arxiv_id: str) -> CitationRecord:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        raise ValueError(f"Missing arXiv entry in {path}")

    authors = []
    for node in entry.findall("atom:author", ns):
        full_name = clean_text(node.findtext("atom:name", default="", namespaces=ns))
        family, given = split_name(full_name)
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)

    published = clean_text(entry.findtext("atom:published", default="", namespaces=ns))
    return CitationRecord(
        source_type="arxiv",
        entry_type="misc",
        title=clean_text(entry.findtext("atom:title", default="", namespaces=ns)),
        authors=" and ".join(authors),
        year=published[:4],
        url=f"https://arxiv.org/abs/{arxiv_id}",
        note=f"arXiv:{arxiv_id}",
        arxiv_id=arxiv_id,
    )


def load_record(identifier_type: str, identifier: str) -> CitationRecord:
    path = cache_path(identifier_type, identifier)
    if not path.exists():
        raise FileNotFoundError(f"Missing cache snapshot for {identifier_type}:{identifier} at {path}")
    if identifier_type == "doi":
        return parse_crossref(path)
    if identifier_type == "pmid":
        return parse_pubmed(path)
    if identifier_type == "arxiv":
        return parse_arxiv(path, identifier)
    raise ValueError(f"Unsupported identifier type: {identifier_type}")


def dedup_key(record: CitationRecord) -> str:
    if record.doi:
        return f"doi:{record.doi.lower()}"
    if record.pmid:
        return f"pmid:{record.pmid}"
    if record.arxiv_id:
        return f"arxiv:{record.arxiv_id}"
    return f"title:{normalize_title(record.title)}"


def record_score(record: CitationRecord) -> int:
    fields = [
        record.authors,
        record.title,
        record.year,
        record.journal,
        record.booktitle,
        record.volume,
        record.number,
        record.pages,
        record.doi,
        record.url,
        record.note,
    ]
    return sum(1 for field in fields if field)


def normalize_title(title: str) -> str:
    title = re.sub(r"[{}\\\\]", "", title)
    return clean_text(title).lower()


def first_word_for_key(title: str) -> str:
    cleaned = re.sub(r"[{}\\\\]", "", title)
    for token in re.findall(r"[A-Za-z0-9]+", cleaned):
        return token.lower()
    return "item"


def first_author_family(authors: str) -> str:
    first = authors.split(" and ")[0].strip()
    if "," in first:
        family = first.split(",", 1)[0]
    else:
        family = first.split()[-1] if first else "Unknown"
    return re.sub(r"[^A-Za-z0-9]+", "", family) or "Unknown"


def make_citation_key(record: CitationRecord) -> str:
    return f"{first_author_family(record.authors)}{record.year}{first_word_for_key(record.title)}"


def format_entry(key: str, record: CitationRecord) -> str:
    field_order = [
        "author",
        "title",
        "journal",
        "booktitle",
        "year",
        "volume",
        "number",
        "pages",
        "doi",
        "url",
        "note",
    ]

    values = OrderedDict()
    values["author"] = record.authors
    values["title"] = record.title
    if record.journal:
        values["journal"] = record.journal
    if record.booktitle:
        values["booktitle"] = record.booktitle
    values["year"] = record.year
    if record.volume:
        values["volume"] = record.volume
    if record.number:
        values["number"] = record.number
    if record.pages:
        values["pages"] = record.pages
    if record.doi:
        values["doi"] = record.doi
    if record.url:
        values["url"] = record.url
    if record.note:
        values["note"] = record.note

    lines = [f"@{record.entry_type}{{{key},"]
    for field_name in field_order:
        if field_name in values:
            lines.append(f"  {field_name} = {{{values[field_name]}}},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    records_by_key: dict[str, CitationRecord] = {}

    for raw_identifier in read_identifiers(INPUT_FILE):
        identifier_type, identifier = identify_identifier(raw_identifier)
        record = load_record(identifier_type, identifier)
        key = dedup_key(record)
        if key not in records_by_key or record_score(record) > record_score(records_by_key[key]):
            records_by_key[key] = record

    used_keys: set[str] = set()
    formatted_entries = []
    for record in sorted(records_by_key.values(), key=make_citation_key):
        key = make_citation_key(record)
        candidate = key
        suffix = ord("a")
        while candidate in used_keys:
            candidate = f"{key}{chr(suffix)}"
            suffix += 1
        used_keys.add(candidate)
        formatted_entries.append(format_entry(candidate, record))

    OUTPUT_FILE.write_text("\n\n".join(formatted_entries) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
