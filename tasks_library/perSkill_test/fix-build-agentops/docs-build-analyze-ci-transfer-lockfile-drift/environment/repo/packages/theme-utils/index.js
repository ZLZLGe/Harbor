function wrapWithFrame({ title, navigation, content }) {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>${title}</title>
  </head>
  <body>
    <header>
      <h1>${title}</h1>
      <nav>
        <ul>
${navigation}
        </ul>
      </nav>
    </header>
    <main>
${content}
    </main>
  </body>
</html>
`;
}

module.exports = {
  wrapWithFrame,
};
