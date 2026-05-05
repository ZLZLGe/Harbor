const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function ensureJson(filePath) {
  assert(fs.existsSync(filePath), `missing file: ${path.relative(ROOT, filePath)}`);
  readJson(filePath);
}

function ensureFile(filePath) {
  assert(fs.existsSync(filePath), `missing file: ${path.relative(ROOT, filePath)}`);
}

function validateStructure() {
  const manifestPath = path.join(ROOT, "package.json");
  ensureJson(manifestPath);
  const manifest = readJson(manifestPath);

  assert(manifest.name, "package.json must define a name");
  assert(manifest.main === "./src/extension.js", "package.json main must point to ./src/extension.js");

  ensureFile(path.join(ROOT, "src", "extension.js"));
  ensureFile(path.join(ROOT, "src", "core.js"));
  ensureFile(path.join(ROOT, "src", "cli-export.js"));

  for (const localeFile of [
    "package.nls.json",
    "package.nls.pt-br.json",
    "package.nls.zh-cn.json",
    "l10n/bundle.l10n.json",
    "l10n/bundle.l10n.pt-br.json",
    "l10n/bundle.l10n.zh-cn.json"
  ]) {
    ensureJson(path.join(ROOT, localeFile));
  }
}

validateStructure();
console.log("validation passed");
