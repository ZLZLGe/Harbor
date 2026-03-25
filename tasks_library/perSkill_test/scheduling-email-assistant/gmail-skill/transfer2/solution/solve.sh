#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const plan = JSON.parse(fs.readFileSync("/root/data/transfer2_follow_up_plan.json", "utf-8"));
const skillDir = "/root/.codex/skills/gmail-skill/scripts";
const drafts = [];

for (const item of plan.draft_requests) {
  const original = JSON.parse(
    execFileSync("node", [path.join(skillDir, "gmail-read.js"), "--id", item.source_message_id], {
      encoding: "utf-8",
    }),
  );

  const body =
    `Hi ${item.candidate_name},\n\n` +
    "Thanks for following up.\n" +
    `Your next step is ${item.next_step}.\n` +
    `Please send any updates by ${item.response_by}.\n\n` +
    "Best,\n" +
    "Talent Ops";

  const draftResult = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "gmail-drafts.js"),
        "--action",
        "create",
        "--to",
        original.from,
        "--subject",
        `Re: ${original.subject}`,
        "--body",
        body,
        "--inReplyTo",
        original.id,
      ],
      { encoding: "utf-8" },
    ),
  );

  drafts.push({
    source_message_id: item.source_message_id,
    draftId: draftResult.id,
  });
}

const payload = {
  campaign_id: plan.campaign_id,
  drafts,
  tool_called: ["gmail_read", "gmail_drafts"],
};

fs.writeFileSync("/root/transfer2_draft_manifest.json", `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
JS
