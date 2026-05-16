import fs from "node:fs/promises";
import path from "node:path";

import { buildCollectionModel, buildPredictiveSearchModel, loadInputs } from "./lib/catalog.mjs";
import { createThemeEngine, renderPage } from "./lib/theme-engine.mjs";

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const outRoot = path.join(workspaceRoot, "out");

async function main() {
  const inputs = await loadInputs();
  const engine = createThemeEngine();
  const collectionModel = buildCollectionModel(inputs);
  const searchModel = buildPredictiveSearchModel(inputs, collectionModel);
  const titleSuffix = inputs.blueprint.layout.title_suffix;

  const collectionContent = await engine.renderFile("main-collection", collectionModel);
  const collectionHtml = await renderPage(
    engine,
    "theme",
    "collection-preview",
    `${collectionModel.collection.title} | ${titleSuffix}`,
    collectionContent
  );

  const searchContent = await engine.renderFile("predictive-search", searchModel);
  const searchHtml = await renderPage(
    engine,
    "theme",
    "predictive-search-preview",
    `Predictive Search | ${titleSuffix}`,
    searchContent
  );

  await fs.mkdir(outRoot, { recursive: true });
  await fs.writeFile(path.join(outRoot, "collection.html"), collectionHtml, "utf-8");
  await fs.writeFile(path.join(outRoot, "predictive-search.html"), searchHtml, "utf-8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
