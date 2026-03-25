const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

const outputPath = "/root/transfer1_triage_report.json";
const readScript = "/root/.codex/skills/gmail-skill/scripts/gmail-read.js";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function readMessage(messageId) {
  return JSON.parse(execFileSync("node", [readScript, "--id", messageId], { encoding: "utf-8" }));
}

assert(fs.existsSync(outputPath), "missing transfer1 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.board_id === "vendor-triage-04", "unexpected board_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["gmail_search", "gmail_read", "gmail_labels"]),
  "unexpected tool_called payload",
);
assert(payload.applied_actions.length === 3, "expected three triage actions");

const expected = {
  "late_arrival": {
    message_id: "vend-2001",
    added_label: "UrgentVendor",
    summary_line: "Truck 44 will miss the 06:00 dock window by 75 minutes.",
  },
  "invoice_hold": {
    message_id: "vend-2002",
    added_label: "BillingReview",
    summary_line: "Please hold payment until the discrepancy is resolved.",
  },
  "temperature_breach": {
    message_id: "vend-2003",
    added_label: "ColdChainAlert",
    summary_line: "Trailer B reported a temperature excursion above 9C during unloading.",
  },
};

for (const action of payload.applied_actions) {
  const exp = expected[action.rule_id];
  assert(exp, `unexpected rule_id ${action.rule_id}`);
  assert(action.message_id === exp.message_id, `unexpected message_id for ${action.rule_id}`);
  assert(action.added_label === exp.added_label, `unexpected label for ${action.rule_id}`);
  assert(action.summary_line === exp.summary_line, `unexpected summary_line for ${action.rule_id}`);

  const message = readMessage(action.message_id);
  assert(message.labels.includes(exp.added_label), `missing label ${exp.added_label} on ${action.message_id}`);
}
