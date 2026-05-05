const fs = require("fs");
const path = require("path");

const SUPPORTED_LOCALES = ["en"];
const FALLBACK_LOCALE = "en";

function normalizeLocale(locale) {
  return String(locale || FALLBACK_LOCALE).toLowerCase();
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readRequest(dataRoot, requestPath) {
  const resolved = requestPath || path.join(dataRoot, "briefing_request.json");
  return readJson(resolved);
}

function readRelease(dataRoot, version) {
  return readJson(path.join(dataRoot, "releases", `${version}.json`));
}

function readTerms(dataRoot, locale) {
  return readJson(path.join(dataRoot, "locales", FALLBACK_LOCALE, "briefing_terms.json"));
}

function readBundle(extensionRoot, locale) {
  return readJson(path.join(extensionRoot, "l10n", "bundle.l10n.json"));
}

function formatPattern(pattern, values) {
  return values.reduce(
    (output, value, index) => output.replaceAll(`{${index}}`, String(value)),
    pattern
  );
}

function pickText(entry, locale) {
  if (!entry || typeof entry !== "object") {
    return "";
  }
  return entry[FALLBACK_LOCALE] || "";
}

function renderBriefing(locale, request, releases, terms, bundle) {
  const lines = [];
  lines.push(`# ${request.title[FALLBACK_LOCALE]}`);
  lines.push("");
  lines.push(`- ${terms.labels.audience}: ${request.audience[FALLBACK_LOCALE]}`);
  lines.push(`- ${terms.labels.versions}: ${request.versions.join(", ")}`);
  lines.push(`- ${terms.labels.focus_areas}: ${request.focus_areas.map((focus) => terms.focus_names[focus] || focus).join(", ")}`);
  lines.push("");
  lines.push(`## ${terms.headings.overview}`);
  lines.push(terms.summary_template.replace("{audience}", request.audience[FALLBACK_LOCALE]));
  lines.push("");
  lines.push(`## ${terms.headings.highlights}`);
  lines.push("");

  for (const release of releases) {
    const selected = release.highlights
      .filter((highlight) => request.focus_areas.includes(highlight.focus))
      .slice(0, request.max_highlights_per_version);

    lines.push(`### VS Code ${release.version}`);
    if (selected.length === 0) {
      lines.push(`- ${bundle["No highlights matched the selected focus areas."]}`);
    } else {
      for (const highlight of selected) {
        lines.push(`- **${pickText(highlight.title, locale)}**: ${pickText(highlight.summary, locale)}`);
      }
    }
    lines.push("");
  }

  lines.push(`## ${terms.headings.actions}`);
  for (const release of releases) {
    const selected = release.highlights
      .filter((highlight) => request.focus_areas.includes(highlight.focus))
      .slice(0, 1);
    for (const highlight of selected) {
      lines.push(`- ${pickText(highlight.action, locale)}`);
    }
  }
  lines.push("");
  lines.push(`> ${bundle["Generated with Release Briefing Explorer"]}`);
  lines.push("");
  return lines.join("\n");
}

function buildBriefings(options = {}) {
  const extensionRoot = options.extensionRoot || path.resolve(__dirname, "..");
  const dataRoot = options.dataRoot || process.env.RELEASE_BRIEFING_DATA_ROOT || "/app/data";
  const outputRoot = options.outputRoot || process.env.RELEASE_BRIEFING_OUTPUT_ROOT || "/app/workspace/output";
  const request = readRequest(dataRoot, options.requestPath);
  const releases = request.versions.map((version) => readRelease(dataRoot, version));

  fs.mkdirSync(outputRoot, { recursive: true });
  const results = [];

  for (const locale of SUPPORTED_LOCALES) {
    const normalized = normalizeLocale(locale);
    const terms = readTerms(dataRoot, normalized);
    const bundle = readBundle(extensionRoot, normalized);
    const content = renderBriefing(normalized, request, releases, terms, bundle);
    const outputPath = path.join(outputRoot, `release-briefing.${normalized}.md`);
    fs.writeFileSync(outputPath, content, "utf8");
    results.push(outputPath);
  }

  return results;
}

function getReleaseIndex(dataRoot) {
  return ["1.89", "1.88", "1.87"].map((version) => {
    const release = readRelease(dataRoot, version);
    return {
      version: release.version,
      published: release.published,
      highlightCount: release.highlights.length
    };
  });
}

function renderReleaseNote(version, locale, dataRoot, extensionRoot) {
  const release = readRelease(dataRoot, version);
  const lines = [`# VS Code ${release.version}`, "", `Published: ${release.published}`, ""];
  for (const highlight of release.highlights) {
    lines.push(`- ${pickText(highlight.title, locale)}: ${pickText(highlight.summary, locale)}`);
  }
  lines.push("");
  return lines.join("\n");
}

module.exports = {
  SUPPORTED_LOCALES,
  buildBriefings,
  getReleaseIndex,
  normalizeLocale,
  renderBriefing,
  renderReleaseNote
};
