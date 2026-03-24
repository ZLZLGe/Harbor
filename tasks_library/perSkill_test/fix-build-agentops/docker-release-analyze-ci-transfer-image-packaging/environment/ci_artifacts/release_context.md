# Release context

- Tag under review: `v2.7.0-rc1`
- Workflow: `.github/workflows/release-image.yml`
- Expected artifacts:
  - container image `ghcr.io/harbor-labs/harbor-app:v2.7.0-rc1`
  - offline bundle `dist/harbor-release-bundle.tgz`
- The release branch already renamed the packaging directory to `packaging/release/`.
- Captured logs from the failed GitHub Actions run are stored in `/workspace/ci_artifacts/logs/`.
