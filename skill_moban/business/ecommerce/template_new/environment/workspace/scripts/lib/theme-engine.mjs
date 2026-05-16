import fs from "node:fs/promises";
import path from "node:path";
import { Liquid } from "liquidjs";

const workspaceRoot = process.env.WORKSPACE_ROOT || "/app/workspace";
const themeRoot = path.join(workspaceRoot, "theme");

function money(value) {
  return `$${Number(value).toFixed(2)}`;
}

export function createThemeEngine() {
  const engine = new Liquid({
    root: [path.join(themeRoot, "sections"), path.join(themeRoot, "layout"), path.join(themeRoot, "snippets")],
    extname: ".liquid",
    strictFilters: false,
    strictVariables: false
  });
  engine.registerFilter("money", money);
  return engine;
}

export async function renderPage(engine, layoutName, pageClass, pageTitle, content) {
  const css = await fs.readFile(path.join(themeRoot, "assets", "theme.css"), "utf-8");
  return engine.renderFile(layoutName, {
    page_class: pageClass,
    page_title: pageTitle,
    inline_css: css,
    content
  });
}
