import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

function dataDir() {
  return process.env.CALENDAR_OFFLINE_STORE_DIR || "/root/calendar";
}

export function loadEvents() {
  const filePath = path.join(dataDir(), "events.json");
  if (!existsSync(filePath)) {
    return [];
  }
  return JSON.parse(readFileSync(filePath, "utf-8"));
}
