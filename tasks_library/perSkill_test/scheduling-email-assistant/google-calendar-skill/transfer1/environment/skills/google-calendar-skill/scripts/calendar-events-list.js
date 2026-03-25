#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadEvents } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));
const timeMin = args.timeMin || "0000-01-01T00:00:00Z";
const timeMax = args.timeMax || "9999-12-31T23:59:59Z";

const events = loadEvents()
  .filter((event) => event.end > timeMin && event.start < timeMax)
  .sort((left, right) => left.start.localeCompare(right.start));

console.log(JSON.stringify({ success: true, count: events.length, events }, null, 2));
