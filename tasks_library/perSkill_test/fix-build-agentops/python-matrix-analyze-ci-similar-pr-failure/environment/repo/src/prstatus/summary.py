def format_python_job(version: str) -> str:
    major, minor = version.split(".", 1)
    return f"python-{major}{minor}"


def build_report_title(pr_number: int, version: str) -> str:
    return f"PR #{pr_number} / {format_python_job(version)}"
