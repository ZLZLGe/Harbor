import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

function dataDir() {
  return process.env.CALENDAR_OFFLINE_STORE_DIR || "/root/calendar";
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

export function loadEvents() {
  return readJson("events.json", []);
}

export function saveEvents(events) {
  writeJson("events.json", events);
}

function loadCounters() {
  return readJson("counters.json", {});
}

function saveCounters(counters) {
  writeJson("counters.json", counters);
}

export function nextId(prefix) {
  const counters = loadCounters();
  const nextValue = (counters[prefix] || 0) + 1;
  counters[prefix] = nextValue;
  saveCounters(counters);
  return `${prefix}-${String(nextValue).padStart(4, "0")}`;
}
