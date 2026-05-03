from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/root/output"))
SERVICE_BASE_URL = os.environ.get("CONTENT_REVIEW_BASE_URL", "http://127.0.0.1:8147")


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        headers={"X-Client": "oracle-solution"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    index = fetch_json("/api/index")
    fetch_json("/api/constraints")
    for doc in index["docs"]:
        fetch_json(f"/api/document/{doc['doc_id']}")

    campaign_summary = """Agent-first product work gets easier to explain when each channel stays grounded in product access, scoped loops, and post-launch feedback.
- X: focus on why agents fail when they only get a thin slice of product context.
- LinkedIn: focus on the team and product decisions that keep agent work tied to a useful workflow.
- Newsletter: focus on the loops that matter after launch, especially instrumentation, dogfooding, and adoption review.
"""

    x_thread = """1/ Most agent products look smart in a demo and weak in daily work for the same reason: the model only sees a thin slice of the product context.
2/ If the agent cannot inspect the same users, sessions, issues, experiments, and history that matter to the task, it turns into a polite question machine instead of a useful tool.
3/ That is why the first product question is not “what should the chat UI look like?” It is “what data, permissions, and loop does this agent need to finish one job well?”
4/ The best early scope is narrow: one repeatable workflow, one visible action path, one measurable outcome. Broad automation promises usually hide weak context and weak trust.
5/ Human review is part of the design, especially when the action cost is high. Users need to see the plan, the touched data, and the uncertainty before they trust the tool.
6/ Then the hard part starts: instrument completion, retries, edits, handoffs, and adoption. Agent products improve when the loop stays visible."""

    linkedin_post = """Teams get into trouble with agent work when they scope the interface before they scope the workflow.\n\nA lot of early agent projects start with a demo that looks polished. Then the team learns the model has partial permissions, partial context, and no durable state. It can answer. It cannot follow through.\n\nThe better sequence is product-first.\n\nDefine one workflow that matters. Decide what records and tools the agent needs. Decide where the user reviews the plan. Decide what happens when confidence drops. Then decide how the interface should present that loop.\n\nThis is also where team decisions matter. If engineering, product, and design are not looking at the same evidence, the project drifts into vague automation language. You need a shared view of scope, workflow fit, retries, edits, and adoption, not only a launch clip.\n\nThe upside is that the work becomes easier to explain. You are not selling an all-purpose assistant. You are building a product surface with context, decisions, and a measurable loop. That is a much better starting point for a team that wants an agent feature people will return to."""

    newsletter = """Subject: The hard part of agent products starts after the first demo
Preview: Product access, dogfooding, and instrumentation matter more than polished autonomy claims.

The easiest way to confuse an agent project is to judge it only by the first demo. A launch clip can make a narrow prompt look complete. Daily use exposes whether the product gave the agent the context, tools, and review points it needs to finish a task inside a workflow people already care about.

## Start with product access

The strongest lesson in the source packet is that agent work breaks when the model only sees a partial slice of the product. If it cannot inspect the same users, sessions, issues, experiments, alerts, and historical decisions that matter to the task, it becomes a shallow layer on top of the product instead of a product surface in its own right. That is why the first planning question is about data, permissions, and state, not about chat chrome.

## Scope the loop before widening the promise

The packet also argues for one narrow workflow before a broad assistant. That framing matters because it changes how teams scope work. A focused loop gives the user a clear starting point, a clear stopping point, and a clear review point. It also gives the team a concrete workflow to inspect when things go wrong. When scope is vague, the model ends up covering for product gaps that should have been solved in the workflow and data model.

## Measure what happens after launch

This is where dogfooding and instrumentation matter. The supporting notes keep pointing to retries, edits after generation, drop-off points, handoffs, and return usage. Those signals tell you whether the agent is helping inside a product loop or simply earning a click. Internal use also shortens the distance between product decisions and user pain. Teams learn faster when they can see the miss, review the session, and connect the behavior to the workflow they actually shipped.

None of this makes agent work less exciting. It makes the bar clearer. Product teams need context, visible review, and evidence loops around the feature. That is how an agent stops looking impressive for one run and starts becoming part of a workflow users trust enough to repeat."""

    source_map = {
        "anchor_asset": "anchor_article.md",
        "deliverables": [
            {
                "file": "x_thread.md",
                "audience": "product engineers experimenting with agent features",
                "content_focus": "context-before-chat-ui",
                "source_refs": [
                    "anchor_article.md#L13-L16",
                    "anchor_article.md#L20-L25",
                    "supporting_context/agent_first_rules.md#L12-L16",
                    "supporting_context/product_for_engineers_about.md#L12-L16",
                ],
            },
            {
                "file": "linkedin_post.md",
                "audience": "engineering leaders deciding how to scope agent work inside product teams",
                "content_focus": "scope-the-loop",
                "source_refs": [
                    "anchor_article.md#L29-L33",
                    "supporting_context/agent_first_rules.md#L20-L31",
                    "supporting_context/posthog_overview.md#L12-L20",
                    "voice_samples/how_we_choose_technologies.md#L8-L17",
                ],
            },
            {
                "file": "newsletter_draft.md",
                "audience": "builders who want a deeper operator view before committing to agent-first product work",
                "content_focus": "instrument-dogfood-iterate",
                "source_refs": [
                    "anchor_article.md#L37-L48",
                    "supporting_context/ai_features_lessons.md#L12-L28",
                    "supporting_context/posthog_overview.md#L18-L24",
                    "voice_samples/using_your_own_product_is_a_superpower.md#L5-L13",
                    "voice_samples/the_hidden_danger_of_shipping_fast.md#L5-L12",
                ],
            },
        ],
        "shared_limits": [
            "No unsupported claims",
            "No recycled paragraphs across channels",
            "No generic hype phrases",
        ],
    }

    publish_gaps = {
        "gaps": [
            {
                "topic": "customer-proof",
                "why_it_matters": "The bundle explains the workflow logic, but it does not include a customer example showing how an agent loop changed a live task outcome.",
                "needed_from_team": "Provide one approved customer or internal case that can be cited in future campaign work.",
            },
            {
                "topic": "numerical-evidence",
                "why_it_matters": "The materials support product and workflow claims, but they do not include approved numbers for adoption, completion, or retry reduction.",
                "needed_from_team": "Confirm whether there are publishable metrics for adoption, completion, edits, or return usage.",
            },
            {
                "topic": "launch-owner",
                "why_it_matters": "The drafts can invite discussion, but they do not specify who owns replies, follow-up links, or final send timing.",
                "needed_from_team": "Assign the owner for CTA links, reply handling, and send timing before publication.",
            },
        ]
    }

    (OUTPUT_ROOT / "campaign_summary.md").write_text(campaign_summary, encoding="utf-8")
    (OUTPUT_ROOT / "x_thread.md").write_text(x_thread + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "linkedin_post.md").write_text(linkedin_post + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "newsletter_draft.md").write_text(newsletter + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "source_map.json").write_text(json.dumps(source_map, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "publish_gaps.json").write_text(json.dumps(publish_gaps, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
