const fs = require("fs");
const path = require("path");

const { getNavigation, getPages } = require("@harbor/content-kit");
const { wrapWithFrame } = require("@harbor/theme-utils");

const docsRoot = path.resolve(__dirname, "..");
const distDir = path.join(docsRoot, "dist");
const outputPath = path.join(distDir, "index.html");

const navHtml = getNavigation()
  .map((item) => `<li><a href="${item.href}">${item.label}</a></li>`)
  .join("\n");

const sectionHtml = getPages()
  .map(
    (page) => `<section id="${page.slug}">
  <h2>${page.title}</h2>
  <p>${page.summary}</p>
</section>`,
  )
  .join("\n");

const html = wrapWithFrame({
  title: "Harbor Docs",
  navigation: navHtml,
  content: sectionHtml,
});

fs.mkdirSync(distDir, { recursive: true });
fs.writeFileSync(outputPath, html);

console.log(`built ${outputPath}`);
