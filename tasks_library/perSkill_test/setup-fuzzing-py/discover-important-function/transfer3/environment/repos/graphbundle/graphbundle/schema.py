def read_declared_type(text: str) -> str:
    text = text.strip()
    if not text.startswith("type="):
        raise ValueError("missing type prefix")
    return text.split("=", 1)[1]
