def summarize_scores(entries: dict[str, int]) -> list[str]:
    ordered = sorted(entries.items(), key=lambda item: (-item[1], item[0]))
    return [f"{name}:{score}" for name, score in ordered]
