#!/usr/bin/env python3
"""
Synthetic support-ticket corpus for skewed n-gram search tests.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

QUEUES = ["billing", "identity", "mailflow", "analytics", "mobile", "fulfillment"]
PRODUCTS = ["atlas sync", "beacon pay", "nova mail", "quarry ops", "lumen mobile", "harbor desk"]
ISSUES = [
    "receipt mismatch",
    "token refresh loop",
    "invoice export timeout",
    "device enrollment failure",
    "duplicate shipment notice",
    "attachment rendering glitch",
    "offline sync drift",
    "dashboard filter regression",
    "session replay gap",
    "refund approval deadlock",
]
ALIASES = {
    "receipt mismatch": "recipt mismatch",
    "token refresh loop": "t0ken refesh loop",
    "invoice export timeout": "invoice xport timeout",
    "device enrollment failure": "device enrolment failur",
    "duplicate shipment notice": "dup shipment notce",
    "attachment rendering glitch": "attch render glitch",
    "offline sync drift": "offlne sync drift",
    "dashboard filter regression": "dashbord filter regresion",
    "session replay gap": "sesion replay gap",
    "refund approval deadlock": "refund aproval deadlock",
}
STEPS = [
    "collect browser trace",
    "rotate service token",
    "rebuild cache segment",
    "compare webhook payloads",
    "replay queue batch",
    "refresh entitlement map",
    "verify tenant policy",
    "capture device manifest",
    "confirm warehouse handoff",
    "audit retry ledger",
]
CHANNELS = ["chat", "email", "voice", "onsite", "bot"]


@dataclass(frozen=True)
class SupportDocument:
    doc_id: int
    ticket_code: str
    title: str
    content: str
    queue: str
    char_length: int


def _word_block(rng: random.Random, issue: str, product: str, queue: str, channel: str, step: str, idx: int) -> str:
    return (
        f"Turn {idx}: customer reports {issue} on {product} via {channel}. "
        f"Queue {queue} validates the account, repeats the symptom wording, and asks for logs. "
        f"Agent records {step}, compares previous incidents, and notes that the customer still sees {issue}. "
        f"Escalation memo keeps the same terminology so fuzzy matching remains useful across typo-heavy queries."
    )


def _make_short_doc(doc_id: int, rng: random.Random) -> SupportDocument:
    queue = rng.choice(QUEUES)
    product = rng.choice(PRODUCTS)
    issue = rng.choice(ISSUES)
    alias = ALIASES[issue]
    channel = rng.choice(CHANNELS)
    title = f"{product} {issue} quick brief"
    bullets = [
        f"Queue: {queue}",
        f"Channel: {channel}",
        f"Primary symptom: {issue}",
        f"Alias often seen in customer text: {alias}",
        f"Immediate step: {rng.choice(STEPS)}",
        f"Resolution hint: confirm the latest {product} state and re-run the customer flow.",
    ]
    content = "\n".join(bullets)
    return SupportDocument(
        doc_id=doc_id,
        ticket_code=f"TKT-{doc_id:05d}",
        title=title,
        content=content,
        queue=queue,
        char_length=len(title) + len(content),
    )


def _make_long_doc(doc_id: int, rng: random.Random) -> SupportDocument:
    queue = rng.choice(QUEUES)
    product = rng.choice(PRODUCTS)
    issue = rng.choice(ISSUES)
    alias = ALIASES[issue]
    channel = rng.choice(CHANNELS)
    title = f"{product} {issue} escalated transcript"
    paragraphs = [
        f"Executive summary: {product} enters a prolonged {issue} case. "
        f"Operators also write the symptom as {alias}. Queue {queue} keeps a detailed timeline."
    ]
    turn_count = rng.randint(60, 120)
    for idx in range(turn_count):
        paragraphs.append(_word_block(rng, issue, product, queue, channel, rng.choice(STEPS), idx))
    paragraphs.append(
        f"Postmortem: {queue} identifies repeated mentions of {issue}, {alias}, and follow-up actions. "
        f"Search traffic usually contains misspellings, partial phrases, and reordered words."
    )
    content = "\n\n".join(paragraphs)
    return SupportDocument(
        doc_id=doc_id,
        ticket_code=f"TKT-{doc_id:05d}",
        title=title,
        content=content,
        queue=queue,
        char_length=len(title) + len(content),
    )


def generate_support_corpus(
    num_documents: int,
    seed: int = 42,
    long_doc_ratio: float = 0.18,
) -> list[SupportDocument]:
    rng = random.Random(seed)
    documents: list[SupportDocument] = []
    long_doc_count = max(1, int(num_documents * long_doc_ratio))
    long_doc_ids = set(rng.sample(range(num_documents), long_doc_count))

    for doc_id in range(num_documents):
        if doc_id in long_doc_ids:
            documents.append(_make_long_doc(doc_id, rng))
        else:
            documents.append(_make_short_doc(doc_id, rng))

    return documents


def _mutate_phrase(text: str, rng: random.Random) -> str:
    chars = list(text)
    if len(chars) > 6 and rng.random() < 0.7:
        drop_at = rng.randrange(1, len(chars) - 1)
        chars.pop(drop_at)
    if len(chars) > 7 and rng.random() < 0.5:
        swap_at = rng.randrange(1, len(chars) - 2)
        chars[swap_at], chars[swap_at + 1] = chars[swap_at + 1], chars[swap_at]
    if rng.random() < 0.5:
        chars.insert(rng.randrange(len(chars)), rng.choice([" ", "-", " "]))
    return "".join(chars)


def generate_query_batch(documents: list[SupportDocument], size: int, seed: int = 99) -> list[str]:
    rng = random.Random(seed)
    queries: list[str] = []
    for _ in range(size):
        doc = rng.choice(documents)
        base = doc.title.replace("quick brief", "").replace("escalated transcript", "").strip()
        if rng.random() < 0.5:
            issue = next((issue for issue in ISSUES if issue in doc.content), "")
            base = f"{base} {issue}".strip()
        if rng.random() < 0.8:
            base = _mutate_phrase(base, rng)
        queries.append(base.lower())
    return queries
