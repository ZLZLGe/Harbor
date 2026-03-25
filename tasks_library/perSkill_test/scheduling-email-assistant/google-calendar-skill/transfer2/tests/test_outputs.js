const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const outputPath = "/root/transfer2_created_holds.json";
assert(fs.existsSync(outputPath), "missing transfer2 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.batch_id === "interview-holds-03", "unexpected batch_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["calendar_events_create"]),
  "unexpected tool_called payload",
);

const listed = JSON.parse(
  execFileSync("node", ["/root/.codex/skills/google-calendar-skill/scripts/calendar-events-list.js"], {
    encoding: "utf-8",
  }),
);

assert(listed.count === 4, "expected four total events after creation");
assert(
  JSON.stringify(payload.created_events) ===
    JSON.stringify([
      { request_id: "hold-1", event_id: "event-0001" },
      { request_id: "hold-2", event_id: "event-0002" },
      { request_id: "hold-3", event_id: "event-0003" },
    ]),
  "unexpected created event manifest",
);
