#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const payload = JSON.parse(fs.readFileSync("/root/data/transfer1_facility_checks.json", "utf-8"));
const skillDir = "/root/.codex/skills/google-calendar-skill/scripts";

const inspections = payload.inspections.map((inspection) => {
  const listed = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "calendar-events-list.js"),
        "--timeMin",
        inspection.window_start,
        "--timeMax",
        inspection.window_end,
      ],
      { encoding: "utf-8" },
    ),
  );

  return {
    inspection_id: inspection.inspection_id,
    overlapping_event_ids: listed.events.map((event) => event.id),
    conflict_count: listed.events.length,
  };
});

fs.writeFileSync(
  "/root/transfer1_conflict_audit.json",
  `${JSON.stringify({ audit_id: payload.audit_id, inspections, tool_called: ["calendar_events_list"] }, null, 2)}\n`,
  "utf-8",
);
JS
