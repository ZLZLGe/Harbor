from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


WORD_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    queue: str
    agent: str
    status: str
    subject: str
    body: str


def load_tickets(path: str) -> list[Ticket]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [
            Ticket(
                ticket_id=row["ticket_id"].strip(),
                queue=row["queue"].strip(),
                agent=row["agent"].strip(),
                status=row["status"].strip(),
                subject=row["subject"].strip(),
                body=row["body"].strip(),
            )
            for row in reader
        ]


def load_stopwords(path: str) -> set[str]:
    return {
        line.strip().lower()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def extract_ticket_terms(ticket: Ticket, stopwords: set[str]) -> tuple[str, ...]:
    text = f"{ticket.subject} {ticket.body}".lower()
    words = WORD_RE.findall(text)
    return tuple(
        sorted(
            {
                word
                for word in words
                if len(word) >= 4 and word not in stopwords
            }
        )
    )


def top_terms(term_counts: Counter[str], limit: int) -> tuple[str, ...]:
    ranked = sorted(term_counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(term for term, _ in ranked[:limit])


def join_terms(values: tuple[str, ...] | list[str]) -> str:
    return ",".join(values) if values else "-"


def build_report_lines(tickets: list[Ticket], stopwords: set[str]) -> list[str]:
    ticket_terms = {
        ticket.ticket_id: extract_ticket_terms(ticket, stopwords)
        for ticket in tickets
    }

    tickets_by_queue: dict[str, list[Ticket]] = defaultdict(list)
    tickets_by_agent: dict[str, list[Ticket]] = defaultdict(list)
    for ticket in tickets:
        tickets_by_queue[ticket.queue].append(ticket)
        tickets_by_agent[ticket.agent].append(ticket)

    queue_rows: list[tuple[str, int, int, int, tuple[str, ...]]] = []
    queue_top_term_sets: dict[str, set[str]] = {}

    for queue, queue_tickets in tickets_by_queue.items():
        term_counts = Counter(
            term
            for ticket in queue_tickets
            for term in ticket_terms[ticket.ticket_id]
        )
        topics = top_terms(term_counts, 5)
        queue_top_term_sets[queue] = set(topics)
        active_count = sum(ticket.status.lower() in {"open", "pending"} for ticket in queue_tickets)
        agent_count = len({ticket.agent for ticket in queue_tickets})
        queue_rows.append((queue, len(queue_tickets), active_count, agent_count, topics))

    queue_rows.sort(key=lambda row: (-row[2], -row[1], row[0]))

    agent_rows: list[tuple[str, int, tuple[str, ...], tuple[str, ...]]] = []
    for agent, agent_tickets in tickets_by_agent.items():
        term_counts = Counter(
            term
            for ticket in agent_tickets
            for term in ticket_terms[ticket.ticket_id]
        )
        queues = tuple(sorted({ticket.queue for ticket in agent_tickets}))
        topics = top_terms(term_counts, 3)
        agent_rows.append((agent, len(agent_tickets), queues, topics))

    agent_rows.sort(key=lambda row: (-len(row[2]), -row[1], row[0]))

    overlap_rows: list[tuple[str, str, tuple[str, ...]]] = []
    for queue_a, queue_b in combinations(sorted(queue_top_term_sets), 2):
        shared = tuple(sorted(queue_top_term_sets[queue_a] & queue_top_term_sets[queue_b]))
        if shared:
            overlap_rows.append((queue_a, queue_b, shared))

    overlap_rows.sort(key=lambda row: (-len(row[2]), row[0], row[1]))

    lines = ["QUEUE SUMMARY"]
    lines.extend(
        f"QUEUE\t{queue}\t{ticket_count}\t{active_count}\t{agent_count}\t{join_terms(list(topics))}"
        for queue, ticket_count, active_count, agent_count, topics in queue_rows
    )
    lines.append("")
    lines.append("AGENT SUMMARY")
    lines.extend(
        f"AGENT\t{agent}\t{ticket_count}\t{','.join(queues)}\t{join_terms(list(topics))}"
        for agent, ticket_count, queues, topics in agent_rows
    )
    lines.append("")
    lines.append("QUEUE OVERLAPS")
    lines.extend(
        f"OVERLAP\t{queue_a}\t{queue_b}\t{join_terms(list(shared))}"
        for queue_a, queue_b, shared in overlap_rows
    )
    return lines


def write_report(input_path: str, stopwords_path: str, output_path: str) -> None:
    tickets = load_tickets(input_path)
    stopwords = load_stopwords(stopwords_path)
    lines = build_report_lines(tickets, stopwords)
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print("Usage: support_topic_report.py <tickets.tsv> <stopwords.txt> <output.txt>", file=sys.stderr)
        return 1
    write_report(argv[0], argv[1], argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
