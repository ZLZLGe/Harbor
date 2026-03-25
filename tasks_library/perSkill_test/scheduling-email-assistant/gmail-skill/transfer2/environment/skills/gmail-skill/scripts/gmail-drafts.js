#!/usr/bin/env node

import { parseArgs } from "./lib/args.js";
import { loadDrafts, nextId, saveDrafts } from "./lib/store.js";

const args = parseArgs(process.argv.slice(2));

if (args.action === "list") {
  const drafts = loadDrafts();
  console.log(JSON.stringify({ success: true, count: drafts.length, drafts }, null, 2));
  process.exit(0);
}

if (args.action !== "create") {
  console.error(JSON.stringify({ success: false, error: "Only --action create or list is supported" }, null, 2));
  process.exit(1);
}

if (!args.to || !args.subject || !args.body) {
  console.error(
    JSON.stringify({ success: false, error: "Missing required arguments: --to, --subject, --body" }, null, 2),
  );
  process.exit(1);
}

const drafts = loadDrafts();
const draftId = nextId("draft");
const draft = {
  id: draftId,
  to: args.to,
  subject: args.subject,
  body: args.body,
  inReplyTo: args.inReplyTo || null,
};

drafts.push(draft);
saveDrafts(drafts);
console.log(JSON.stringify({ success: true, id: draftId, draft }, null, 2));
