const fs = require("node:fs");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const outputPath = "/root/transfer3_update_log.json";
assert(fs.existsSync(outputPath), "missing transfer3 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.batch_id === "training-updates-02", "unexpected batch_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["calendar_events_update"]),
  "unexpected tool_called payload",
);

const events = JSON.parse(fs.readFileSync("/root/calendar/events.json", "utf-8"));
const lookup = Object.fromEntries(events.map((event) => [event.id, event]));

assert(lookup["evt-u1"].start === "2026-07-01T09:30:00Z", "evt-u1 start not updated");
assert(lookup["evt-u2"].start === "2026-07-01T12:00:00Z", "evt-u2 start not updated");
assert(lookup["evt-u3"].end === "2026-07-02T16:30:00Z", "evt-u3 end not updated");
