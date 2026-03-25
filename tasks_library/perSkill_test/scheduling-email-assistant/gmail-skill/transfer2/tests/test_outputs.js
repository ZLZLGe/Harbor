const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

const outputPath = "/root/transfer2_draft_manifest.json";
const listScript = "/root/.codex/skills/gmail-skill/scripts/gmail-drafts.js";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(fs.existsSync(outputPath), "missing transfer2 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));
assert(payload.campaign_id === "candidate-follow-up-pack-02", "unexpected campaign_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["gmail_read", "gmail_drafts"]),
  "unexpected tool_called payload",
);

const listed = JSON.parse(execFileSync("node", [listScript, "--action", "list"], { encoding: "utf-8" }));
assert(listed.count === 3, "expected three drafts");

const expectedBodies = {
  "draft-0001":
    "Hi Elena Park,\n\n" +
    "Thanks for following up.\n" +
    "Your next step is a portfolio review with the product panel.\n" +
    "Please send any updates by March 20, 2026.\n\n" +
    "Best,\n" +
    "Talent Ops",
  "draft-0002":
    "Hi Marcus Bell,\n\n" +
    "Thanks for following up.\n" +
    "Your next step is a scheduling check with the finance team.\n" +
    "Please send any updates by March 21, 2026.\n\n" +
    "Best,\n" +
    "Talent Ops",
  "draft-0003":
    "Hi Priya Nanda,\n\n" +
    "Thanks for following up.\n" +
    "Your next step is a take-home recap with the analytics lead.\n" +
    "Please send any updates by March 22, 2026.\n\n" +
    "Best,\n" +
    "Talent Ops",
};

for (const entry of payload.drafts) {
  const draft = listed.drafts.find((item) => item.id === entry.draftId);
  assert(draft, `missing draft ${entry.draftId}`);
  assert(draft.body === expectedBodies[entry.draftId], `unexpected body for ${entry.draftId}`);
}
