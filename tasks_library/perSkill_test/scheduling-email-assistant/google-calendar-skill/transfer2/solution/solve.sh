#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const payload = JSON.parse(fs.readFileSync("/root/data/transfer2_interview_holds.json", "utf-8"));
const skillDir = "/root/.codex/skills/google-calendar-skill/scripts";

const createdEvents = payload.hold_requests.map((request) => {
  const result = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "calendar-events-create.js"),
        "--summary",
        request.summary,
        "--start",
        request.start,
        "--end",
        request.end,
      ],
      { encoding: "utf-8" },
    ),
  );
  return {
    request_id: request.request_id,
    event_id: result.event.id,
  };
});

fs.writeFileSync(
  "/root/transfer2_created_holds.json",
  `${JSON.stringify({ batch_id: payload.batch_id, created_events: createdEvents, tool_called: ["calendar_events_create"] }, null, 2)}\n`,
  "utf-8",
);
JS
