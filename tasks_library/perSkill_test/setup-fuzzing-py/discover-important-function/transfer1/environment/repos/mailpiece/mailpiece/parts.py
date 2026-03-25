def parse_boundary_section(body: str, boundary: str) -> list[str]:
    if not boundary:
        raise ValueError("missing boundary")
    marker = f"--{boundary}"
    sections = [chunk.strip() for chunk in body.split(marker) if chunk.strip() and chunk.strip() != "--"]
    return sections
