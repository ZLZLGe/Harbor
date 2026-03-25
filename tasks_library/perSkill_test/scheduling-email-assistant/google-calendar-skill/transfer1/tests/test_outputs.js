const fs = require("node:fs");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const outputPath = "/root/transfer1_conflict_audit.json";
assert(fs.existsSync(outputPath), "missing transfer1 output");
const payload = JSON.parse(fs.readFileSync(outputPath, "utf-8"));

assert(payload.audit_id === "facility-conflicts-02", "unexpected audit_id");
assert(
  JSON.stringify(payload.tool_called) === JSON.stringify(["calendar_events_list"]),
  "unexpected tool_called payload",
);
assert(
  JSON.stringify(payload.inspections) ===
    JSON.stringify([
      { inspection_id: "insp-1", overlapping_event_ids: ["evt-f1", "evt-f2"], conflict_count: 2 },
      { inspection_id: "insp-2", overlapping_event_ids: [], conflict_count: 0 },
      { inspection_id: "insp-3", overlapping_event_ids: ["evt-f4"], conflict_count: 1 },
    ]),
  "unexpected inspection audit payload",
);
