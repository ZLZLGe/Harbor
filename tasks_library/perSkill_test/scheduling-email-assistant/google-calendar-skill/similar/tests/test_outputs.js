const fs = require("node:fs");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const outputPath = "/root/similar_calendar_proposals.json";
assert(fs.existsSync(outputPath), "missing similar output");

const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));
assert(payload.batch_id === "calendar-proposals-01", "unexpected batch_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["calendar_events_list"]),
  "unexpected tool_called payload",
);
assert(
  JSON.stringify(payload.proposals) ===
    JSON.stringify([
      {
        request_id: "slot-1",
        proposed_start: "2026-01-08T12:00:00Z",
        proposed_end: "2026-01-08T13:00:00Z",
      },
      {
        request_id: "slot-2",
        proposed_start: "2026-01-09T11:00:00Z",
        proposed_end: "2026-01-09T12:30:00Z",
      },
      {
        request_id: "slot-3",
        proposed_start: "2026-01-06T09:30:00Z",
        proposed_end: "2026-01-06T10:15:00Z",
      },
    ]),
  "unexpected proposal payload",
);
