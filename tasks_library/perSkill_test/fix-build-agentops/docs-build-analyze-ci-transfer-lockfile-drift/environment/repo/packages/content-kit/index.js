function getNavigation() {
  return [
    { label: "Getting Started", href: "#getting-started" },
    { label: "Deploy", href: "#deploy" },
  ];
}

function getPages() {
  return [
    {
      slug: "getting-started",
      title: "Getting Started",
      summary: "Install the CLI and bootstrap a Harbor deployment.",
    },
    {
      slug: "deploy",
      title: "Deployment Checklist",
      summary: "Verify credentials, storage, and rollout policies before release.",
    },
  ];
}

module.exports = {
  getNavigation,
  getPages,
};
