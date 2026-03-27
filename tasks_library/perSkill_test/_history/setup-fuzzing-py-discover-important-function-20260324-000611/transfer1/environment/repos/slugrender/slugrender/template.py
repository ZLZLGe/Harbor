import json


def parse_slug_template(raw: str) -> list[str]:
    """Parse a slug template into literal and token segments."""
    return [part for part in raw.split("{") if part]


def load_template_bundle(raw: str) -> dict[str, str]:
    """Load a JSON bundle of named slug templates."""
    bundle = json.loads(raw)
    return {item["name"]: item["template"] for item in bundle["templates"]}


def render_slug(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered
