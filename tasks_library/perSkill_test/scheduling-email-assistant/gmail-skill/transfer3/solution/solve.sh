#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const plan = JSON.parse(fs.readFileSync("/root/data/transfer3_escalation_plan.json", "utf-8"));
const skillDir = "/root/.codex/skills/gmail-skill/scripts";
const sentResults = [];

for (const item of plan.escalations) {
  const original = JSON.parse(
    execFileSync("node", [path.join(skillDir, "gmail-read.js"), "--id", item.source_message_id], {
      encoding: "utf-8",
    }),
  );

  const body =
    `Escalation reason: ${item.reason}\n` +
    `Original sender: ${original.from}\n` +
    `Original subject: ${original.subject}\n\n` +
    "Original message:\n" +
    `${original.body}`;

  const sent = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "gmail-send.js"),
        "--to",
        "compliance.board@example.com",
        "--subject",
        `Escalation: ${original.subject}`,
        "--body",
        body,
      ],
      { encoding: "utf-8" },
    ),
  );

  sentResults.push({
    source_message_id: item.source_message_id,
    messageId: sent.messageId,
  });
}

const payload = {
  batch_id: plan.batch_id,
  sent_results: sentResults,
  tool_called: ["gmail_read", "gmail_send"],
};

fs.writeFileSync("/root/transfer3_escalation_log.json", `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
JS
