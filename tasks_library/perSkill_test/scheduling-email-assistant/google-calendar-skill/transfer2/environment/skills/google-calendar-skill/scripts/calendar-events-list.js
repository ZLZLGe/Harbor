#!/usr/bin/env node

import { loadEvents } from "./lib/store.js";

console.log(JSON.stringify({ success: true, count: loadEvents().length, events: loadEvents() }, null, 2));
