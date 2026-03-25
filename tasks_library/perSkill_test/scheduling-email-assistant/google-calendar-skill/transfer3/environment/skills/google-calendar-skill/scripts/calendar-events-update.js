#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadEvents, saveEvents } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (!args.id || !args.start || !args.end) {
  console.error(JSON.stringify({ success: false, error: "Missing required arguments: --id, --start, --end" }, null, 2));
  process.exit(1);
}

const events = loadEvents();
const event = events.find((item) => item.id === args.id);

if (!event) {
  console.error(JSON.stringify({ success: false, error: `Event not found: ${args.id}` }, null, 2));
  process.exit(1);
}

event.start = args.start;
event.end = args.end;
saveEvents(events);

console.log(JSON.stringify({ success: true, event }, null, 2));
