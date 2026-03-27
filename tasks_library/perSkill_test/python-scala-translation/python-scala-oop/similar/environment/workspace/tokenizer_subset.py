from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class TokenType:
    STRING = "string"
    NUMERIC = "numeric"


@dataclass(frozen=True)
class Token:
    value: str
    token_type: str
    metadata: dict[str, str] = field(default_factory=dict)

    def with_metadata(self, **kwargs):
        return Token(self.value, self.token_type, {**self.metadata, **kwargs})


class BaseTokenizer(ABC):
    @abstractmethod
    def tokenize(self, value):
        pass

    def tokenize_batch(self, values):
        return [self.tokenize(v) for v in values]


class StringTokenizer(BaseTokenizer):
    def tokenize(self, value):
        return Token(str(value), TokenType.STRING)


class NumericTokenizer(BaseTokenizer):
    def tokenize(self, value):
        return Token(str(value), TokenType.NUMERIC)


class TokenizerBuilder:
    @staticmethod
    def to_token(value):
        if isinstance(value, str):
            return StringTokenizer().tokenize(value)
        return NumericTokenizer().tokenize(value)
