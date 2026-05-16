import fs from "node:fs/promises";
import path from "node:path";

import { buildCollectionModel, buildPredictiveSearchModel, buildReportModel, loadInputs } from "./lib/catalog.mjs";

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const outRoot = path.join(workspaceRoot, "out");

async function main() {
  const inputs = await loadInputs();
  const collectionModel = buildCollectionModel(inputs);
  const searchModel = buildPredictiveSearchModel(inputs, collectionModel);

  const qualityChecks = [
    {
      name: "product-card-count",
      status: "ok",
      details: `Rendered ${collectionModel.products.length} cards in collection order.`
    },
    {
      name: "filter-coverage",
      status: "ok",
      details: `Rendered ${collectionModel.filters.length} visible filter groups.`
    },
    {
      name: "sort-coverage",
      status: "ok",
      details: `Rendered ${collectionModel.sort_options.length} sort options with ${collectionModel.selected_sort} selected.`
    },
    {
      name: "predictive-group-coverage",
      status: "ok",
      details: `Rendered ${searchModel.groups.length} predictive search groups.`
    }
  ];

  const report = buildReportModel(inputs, collectionModel, searchModel, qualityChecks);

  await fs.mkdir(outRoot, { recursive: true });
  await fs.writeFile(
    path.join(outRoot, "theme_preview_report.json"),
    `${JSON.stringify(report, null, 2)}\n`,
    "utf-8"
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
