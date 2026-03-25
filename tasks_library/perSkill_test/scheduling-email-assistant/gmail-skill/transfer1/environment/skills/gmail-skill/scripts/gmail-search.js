#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadMessages, makeSnippet } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));
const query = (args.query || "").trim();
const limit = Number(args.limit || "50");
const tokens = query ? query.split(/\s+/) : [];

function matchesToken(message, token) {
  const lower = token.toLowerCase();
  if (lower.startsWith("label:")) {
    const label = token.slice(6).toLowerCase();
    return message.labels.some((item) => item.toLowerCase() === label);
  }
  if (lower === "is:unread") {
    return message.labels.includes("UNREAD");
  }
  if (lower === "is:read") {
    return !message.labels.includes("UNREAD");
  }
  if (lower.startsWith("from:")) {
    return message.from.toLowerCase().includes(token.slice(5).toLowerCase());
  }
  if (lower.startsWith("subject:")) {
    return message.subject.toLowerCase().includes(token.slice(8).toLowerCase());
  }
  return `${message.subject}\n${message.body}`.toLowerCase().includes(lower);
}

const messages = loadMessages()
  .filter((message) => tokens.every((token) => matchesToken(message, token)))
  .slice(0, limit)
  .map((message) => ({
    id: message.id,
    threadId: message.threadId,
    from: message.from,
    to: message.to,
    subject: message.subject,
    date: message.date,
    labels: message.labels,
    snippet: makeSnippet(message.body),
  }));

console.log(JSON.stringify({ success: true, count: messages.length, messages }, null, 2));
