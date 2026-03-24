# Docs deploy context

- Pull request: `#218`
- Branch: `docs/add-search-sidebar`
- Workflow: `.github/workflows/docs-site.yml`
- Symptom: the static docs site stopped building in CI after a dependency refresh for the docs theme.
- Expected outcome: both docs jobs should install dependencies with `npm ci` and finish the docs build smoke check.
