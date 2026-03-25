#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadMessages, makeSnippet, nextId, saveMessages } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (!args.to || !args.subject || !args.body) {
  console.error(
    JSON.stringify({ success: false, error: "Missing required arguments: --to, --subject, --body" }, null, 2),
  );
  process.exit(1);
}

const messages = loadMessages();
const messageId = nextId("sent");
const threadId = args.threadId || messageId;
const fromAddress = process.env.GMAIL_OFFLINE_FROM || "opsdesk@example.com";

const message = {
  id: messageId,
  threadId,
  from: fromAddress,
  to: args.to,
  subject: args.subject,
  date: args.date || "2026-01-04T00:00:00Z",
  labels: ["SENT"],
  body: args.body,
};

messages.push(message);
saveMessages(messages);

console.log(
  JSON.stringify(
    {
      success: true,
      messageId,
      threadId,
      to: message.to,
      subject: message.subject,
      snippet: makeSnippet(message.body),
    },
    null,
    2,
  ),
);
