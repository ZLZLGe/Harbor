#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { findMessage, makeSnippet } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (!args.id) {
  console.error(JSON.stringify({ success: false, error: "Missing required argument: --id" }, null, 2));
  process.exit(1);
}

const message = findMessage(args.id);

if (!message) {
  console.error(JSON.stringify({ success: false, error: `Message not found: ${args.id}` }, null, 2));
  process.exit(1);
}

console.log(
  JSON.stringify(
    {
      success: true,
      id: message.id,
      threadId: message.threadId,
      from: message.from,
      to: message.to,
      subject: message.subject,
      date: message.date,
      labels: message.labels,
      snippet: makeSnippet(message.body),
      body: message.body,
    },
    null,
    2,
  ),
);
