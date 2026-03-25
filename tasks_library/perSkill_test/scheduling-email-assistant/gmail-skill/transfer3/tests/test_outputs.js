const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

const outputPath = "/root/transfer3_escalation_log.json";
const readScript = "/root/.codex/skills/gmail-skill/scripts/gmail-read.js";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function readMessage(messageId) {
  return JSON.parse(execFileSync("node", [readScript, "--id", messageId], { encoding: "utf-8" }));
}

assert(fs.existsSync(outputPath), "missing transfer3 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.batch_id === "compliance-escalations-03", "unexpected batch_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["gmail_read", "gmail_send"]),
  "unexpected tool_called payload",
);
assert(payload.sent_results.length === 3, "expected three sent escalation messages");

const expectedSubjects = {
  "comp-4001": "Escalation: Export packet missing attachment",
  "comp-4002": "Escalation: Request for pricing exception",
  "comp-4003": "Escalation: Weekend loading request",
};

for (const entry of payload.sent_results) {
  const sent = readMessage(entry.messageId);
  assert(sent.to === "compliance.board@example.com", `unexpected recipient for ${entry.source_message_id}`);
  assert(sent.subject === expectedSubjects[entry.source_message_id], `unexpected subject for ${entry.source_message_id}`);
  assert(sent.body.includes("Escalation reason:"), `missing reason header for ${entry.source_message_id}`);
  assert(sent.body.includes("Original message:"), `missing original message block for ${entry.source_message_id}`);
}
