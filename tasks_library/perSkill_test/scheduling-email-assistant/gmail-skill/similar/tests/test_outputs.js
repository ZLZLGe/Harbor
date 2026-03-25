const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

const outputPath = "/root/similar_sent_results.json";
const readScript = "/root/.codex/skills/gmail-skill/scripts/gmail-read.js";

const expectedBodies = {
  "msg-1001":
    "Hi,\n\n" +
    "Thank you for your meeting request.\n\n" +
    "I can be available:\n\n" +
    "Date: Thursday, January 08, 2026\n" +
    "Time: 12:00 PM - 01:00 PM\n" +
    "Duration: 1.0 hour(s)\n\n" +
    "If this time doesn't work, please let me know your preferred alternatives.\n\n" +
    "Best regards,\n" +
    "Ops Desk",
  "msg-1002":
    "Hi,\n\n" +
    "Thank you for your meeting request.\n\n" +
    "I can be available:\n\n" +
    "Date: Friday, January 09, 2026\n" +
    "Time: 11:00 AM - 12:30 PM\n" +
    "Duration: 1.5 hour(s)\n\n" +
    "If this time doesn't work, please let me know your preferred alternatives.\n\n" +
    "Best regards,\n" +
    "Ops Desk",
  "msg-1003":
    "Hi,\n\n" +
    "Thank you for your meeting request.\n\n" +
    "I can be available:\n\n" +
    "Date: Tuesday, January 06, 2026\n" +
    "Time: 09:30 AM - 10:15 AM\n" +
    "Duration: 0.75 hour(s)\n\n" +
    "If this time doesn't work, please let me know your preferred alternatives.\n\n" +
    "Best regards,\n" +
    "Ops Desk",
};

const expectedRecipients = {
  "msg-1001": "john.smith@example.com",
  "msg-1002": "rwilson@example.consulting.net",
  "msg-1003": "amanda.lee@example.hr-solutions.com",
};

const expectedSubjects = {
  "msg-1001": "Re: Meeting request for January 8",
  "msg-1002": "Re: Project review scheduling request",
  "msg-1003": "Re: Interview availability",
};

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function readMessage(messageId) {
  return JSON.parse(execFileSync("node", [readScript, "--id", messageId], { encoding: "utf-8" }));
}

assert(fs.existsSync(outputPath), "missing similar output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.batch_id === "meeting-replies-01", "unexpected batch_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["gmail_read", "gmail_send"]),
  "unexpected tool_called payload",
);
assert(
  JSON.stringify(payload.sent_results.map((item) => item.request_message_id)) ===
    JSON.stringify(["msg-1001", "msg-1002", "msg-1003"]),
  "unexpected sent_results order",
);

for (const entry of payload.sent_results) {
  const sent = readMessage(entry.messageId);
  const requestId = entry.request_message_id;
  assert(sent.to === expectedRecipients[requestId], `unexpected recipient for ${requestId}`);
  assert(sent.subject === expectedSubjects[requestId], `unexpected subject for ${requestId}`);
  assert(sent.body === expectedBodies[requestId], `unexpected body for ${requestId}`);
}
