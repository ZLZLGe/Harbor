#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadMessages, saveMessages } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (args.action !== "add") {
  console.error(JSON.stringify({ success: false, error: "Only --action add is supported" }, null, 2));
  process.exit(1);
}

if (!args.id || !args.label) {
  console.error(JSON.stringify({ success: false, error: "Missing required arguments: --id, --label" }, null, 2));
  process.exit(1);
}

const messages = loadMessages();
const message = messages.find((item) => item.id === args.id);

if (!message) {
  console.error(JSON.stringify({ success: false, error: `Message not found: ${args.id}` }, null, 2));
  process.exit(1);
}

if (!message.labels.includes(args.label)) {
  message.labels.push(args.label);
}

saveMessages(messages);
console.log(JSON.stringify({ success: true, id: message.id, labels: message.labels }, null, 2));
