import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

function dataDir() {
  return process.env.GMAIL_OFFLINE_STORE_DIR || "/root/mailbox";
}

function readJson(fileName, fallback) {
  const filePath = path.join(dataDir(), fileName);
  if (!existsSync(filePath)) {
    return fallback;
  }
  return JSON.parse(readFileSync(filePath, "utf-8"));
}

function writeJson(fileName, payload) {
  mkdirSync(dataDir(), { recursive: true });
  writeFileSync(path.join(dataDir(), fileName), `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
}

export function loadMessages() {
  return readJson("messages.json", []);
}

export function saveMessages(messages) {
  writeJson("messages.json", messages);
}

export function findMessage(messageId) {
  return loadMessages().find((message) => message.id === messageId) || null;
}

export function makeSnippet(body) {
  return body.replace(/\s+/g, " ").trim().slice(0, 120);
}
