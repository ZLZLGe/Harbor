#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const payload = JSON.parse(fs.readFileSync("/root/data/transfer3_training_updates.json", "utf-8"));
const skillDir = "/root/.codex/skills/google-calendar-skill/scripts";

const updatedEvents = payload.updates.map((item) => {
  JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "calendar-events-update.js"),
        "--id",
        item.event_id,
        "--start",
        item.new_start,
        "--end",
        item.new_end,
      ],
      { encoding: "utf-8" },
    ),
  );
  return {
    event_id: item.event_id,
    new_start: item.new_start,
    new_end: item.new_end,
  };
});

fs.writeFileSync(
  "/root/transfer3_update_log.json",
  `${JSON.stringify({ batch_id: payload.batch_id, updated_events: updatedEvents, tool_called: ["calendar_events_update"] }, null, 2)}\n`,
  "utf-8",
);
JS
