#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const plan = JSON.parse(fs.readFileSync("/root/data/similar_reply_plan.json", "utf-8"));
const skillDir = "/root/.codex/skills/gmail-skill/scripts";
const results = [];

for (const item of plan.replies) {
  const original = JSON.parse(
    execFileSync("node", [path.join(skillDir, "gmail-read.js"), "--id", item.request_message_id], {
      encoding: "utf-8",
    }),
  );

  const body =
    "Hi,\n\n" +
    "Thank you for your meeting request.\n\n" +
    "I can be available:\n\n" +
    `Date: ${item.date}\n` +
    `Time: ${item.time}\n` +
    `Duration: ${item.duration_hours} hour(s)\n\n` +
    "If this time doesn't work, please let me know your preferred alternatives.\n\n" +
    "Best regards,\n" +
    "Ops Desk";

  const sent = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "gmail-send.js"),
        "--to",
        original.from,
        "--subject",
        `Re: ${original.subject}`,
        "--body",
        body,
        "--threadId",
        original.threadId,
      ],
      { encoding: "utf-8" },
    ),
  );

  results.push({
    request_message_id: item.request_message_id,
    messageId: sent.messageId,
  });
}

const payload = {
  batch_id: plan.batch_id,
  sent_results: results,
  tool_called: ["gmail_read", "gmail_send"],
};

fs.writeFileSync("/root/similar_sent_results.json", `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
JS
