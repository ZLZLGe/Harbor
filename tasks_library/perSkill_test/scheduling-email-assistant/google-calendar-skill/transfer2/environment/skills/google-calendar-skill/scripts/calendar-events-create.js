#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadEvents, nextId, saveEvents } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (!args.summary || !args.start || !args.end) {
  console.error(JSON.stringify({ success: false, error: "Missing required arguments: --summary, --start, --end" }, null, 2));
  process.exit(1);
}

const events = loadEvents();
const id = nextId("event");
const event = {
  id,
  summary: args.summary,
  start: args.start,
  end: args.end,
  status: "confirmed",
};

events.push(event);
saveEvents(events);

console.log(JSON.stringify({ success: true, event }, null, 2));
