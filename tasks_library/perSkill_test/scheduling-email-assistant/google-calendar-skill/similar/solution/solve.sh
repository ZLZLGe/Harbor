#!/bin/bash
set -euo pipefail

node <<'JS'
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

function addMinutes(isoString, minutes) {
  return new Date(new Date(isoString).getTime() + minutes * 60000).toISOString().replace(".000", "");
}

const payload = JSON.parse(fs.readFileSync("/root/data/similar_meeting_windows.json", "utf-8"));
const skillDir = "/root/.codex/skills/google-calendar-skill/scripts";
const proposals = [];

for (const request of payload.requests) {
  const listed = JSON.parse(
    execFileSync(
      "node",
      [
        path.join(skillDir, "calendar-events-list.js"),
        "--timeMin",
        request.window_start,
        "--timeMax",
        request.window_end,
      ],
      { encoding: "utf-8" },
    ),
  );

  let cursor = request.window_start;
  let chosenStart = null;
  let chosenEnd = null;

  for (const event of listed.events) {
    const candidateEnd = addMinutes(cursor, request.duration_minutes);
    if (candidateEnd <= event.start) {
      chosenStart = cursor;
      chosenEnd = candidateEnd;
      break;
    }
    if (event.end > cursor) {
      cursor = event.end;
    }
  }

  if (!chosenStart) {
    const finalEnd = addMinutes(cursor, request.duration_minutes);
    if (finalEnd <= request.window_end) {
      chosenStart = cursor;
      chosenEnd = finalEnd;
    }
  }

  proposals.push({
    request_id: request.request_id,
    proposed_start: chosenStart,
    proposed_end: chosenEnd,
  });
}

fs.writeFileSync(
  "/root/similar_calendar_proposals.json",
  `${JSON.stringify({ batch_id: payload.batch_id, proposals, tool_called: ["calendar_events_list"] }, null, 2)}\n`,
  "utf-8",
);
JS
