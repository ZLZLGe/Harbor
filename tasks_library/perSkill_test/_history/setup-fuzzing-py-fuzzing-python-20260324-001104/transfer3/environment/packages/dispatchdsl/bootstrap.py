from .tokenizer import tokenize
from .validator import validate_tokens


def load_config(text: str) -> dict[str, object]:
    tokens = tokenize(text)
    return validate_tokens(tokens)
