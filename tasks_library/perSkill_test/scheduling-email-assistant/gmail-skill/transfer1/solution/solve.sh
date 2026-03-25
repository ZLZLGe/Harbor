#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const rules = JSON.parse(fs.readFileSync("/root/data/transfer1_triage_rules.json", "utf-8"));
const skillDir = "/root/.codex/skills/gmail-skill/scripts";
const applied = [];

for (const rule of rules.rules) {
  const searchResult = JSON.parse(
    execFileSync("node", [path.join(skillDir, "gmail-search.js"), "--query", rule.query], { encoding: "utf-8" }),
  );

  for (const candidate of searchResult.messages) {
    const fullMessage = JSON.parse(
      execFileSync("node", [path.join(skillDir, "gmail-read.js"), "--id", candidate.id], { encoding: "utf-8" }),
    );

    if (!fullMessage.body.includes(rule.contains_phrase)) {
      continue;
    }

    JSON.parse(
      execFileSync(
        "node",
        [path.join(skillDir, "gmail-labels.js"), "--action", "add", "--id", candidate.id, "--label", rule.add_label],
        { encoding: "utf-8" },
      ),
    );

    const summaryLine = fullMessage.body.split(".")[0].trim() + ".";
    applied.push({
      rule_id: rule.rule_id,
      message_id: candidate.id,
      subject: fullMessage.subject,
      added_label: rule.add_label,
      summary_line: summaryLine,
    });
  }
}

const payload = {
  board_id: rules.board_id,
  applied_actions: applied,
  tool_called: ["gmail_search", "gmail_read", "gmail_labels"],
};

fs.writeFileSync("/root/transfer1_triage_report.json", `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
JS
