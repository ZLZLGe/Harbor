def tokenize(text: str) -> list[str]:
    parts = [segment.strip() for segment in text.split(";") if segment.strip()]
    if not parts:
        return []
    return parts
