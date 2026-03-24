from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal, ROUND_HALF_UP


def round_score(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


@dataclass(frozen=True)
class RubricQuestion:
    question_id: str
    prompt: str
    max_points: float
    weight: float = 1.0
    keywords: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "RubricQuestion":
        keywords = tuple(
            normalize_text(str(item))
            for item in payload.get("keywords", ())
            if str(item).strip()
        )
        metadata_payload = payload.get("metadata", {})
        metadata = {
            str(key): str(value).strip()
            for key, value in dict(metadata_payload).items()
        }
        return cls(
            question_id=str(payload["question_id"]).strip(),
            prompt=str(payload["prompt"]).strip(),
            max_points=round_score(float(payload["max_points"])),
            weight=round_score(float(payload.get("weight", 1.0))),
            keywords=keywords,
            metadata=metadata,
        )

    @property
    def max_weighted(self) -> float:
        return round_score(self.max_points * self.weight)


@dataclass(frozen=True)
class ScoreResult:
    question_id: str
    scorer_kind: str
    raw_score: float
    max_points: float
    weighted_score: float
    feedback: str
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        if self.max_points == 0:
            return 0.0
        return round_score(self.raw_score / self.max_points)

    @classmethod
    def from_evaluation(
        cls,
        question: RubricQuestion,
        scorer_kind: str,
        raw_score: float,
        feedback: str,
        metadata: Mapping[str, object] | None = None,
    ) -> "ScoreResult":
        bounded = round_score(clamp(raw_score, 0.0, question.max_points))
        meta = {
            str(key): str(value)
            for key, value in dict(metadata or {}).items()
        }
        return cls(
            question_id=question.question_id,
            scorer_kind=scorer_kind,
            raw_score=bounded,
            max_points=question.max_points,
            weighted_score=round_score(bounded * question.weight),
            feedback=feedback.strip(),
            metadata=meta,
        )

    def with_metadata(self, **kwargs: object) -> "ScoreResult":
        merged = {
            **self.metadata,
            **{str(key): str(value) for key, value in kwargs.items()},
        }
        return replace(self, metadata=merged)

    def render(self) -> str:
        return (
            f"{self.question_id}|{self.scorer_kind}|{self.raw_score:.4f}|"
            f"{self.weighted_score:.4f}|{self.ratio:.4f}|{self.feedback}"
        )


class AbstractScorer(ABC):
    kind = "abstract"

    def __init__(self, kind: str | None = None) -> None:
        if kind is not None:
            self.kind = kind

    @abstractmethod
    def score_raw(self, question: RubricQuestion, response: str) -> tuple[float, str]:
        raise NotImplementedError

    def build_result(self, question: RubricQuestion, response: str, **metadata: object) -> ScoreResult:
        raw_score, feedback = self.score_raw(question, response)
        base_metadata: dict[str, object] = {
            "prompt": question.prompt,
            "response_chars": len(response.strip()),
            **question.metadata,
        }
        base_metadata.update(metadata)
        return ScoreResult.from_evaluation(question, self.kind, raw_score, feedback, base_metadata)

    def score(self, question: RubricQuestion, response: str) -> ScoreResult:
        return self.build_result(question, response)


class TextRubricScorer(AbstractScorer):
    def __init__(self, min_length: int = 0, bonus_points: float = 0.0) -> None:
        super().__init__("text")
        self.min_length = min_length
        self.bonus_points = bonus_points

    def score_raw(self, question: RubricQuestion, response: str) -> tuple[float, str]:
        normalized = normalize_text(response)
        if not normalized:
            return 0.0, "blank response"

        if not question.keywords:
            raw_score = question.max_points if len(normalized) >= self.min_length else 0.0
            feedback = "free response accepted" if raw_score else "response too short"
            return round_score(raw_score), feedback

        matched = [keyword for keyword in question.keywords if keyword in normalized]
        ratio = len(matched) / len(question.keywords)
        raw_score = question.max_points * ratio
        if ratio == 1.0 and len(normalized) >= self.min_length:
            raw_score += self.bonus_points

        feedback = f"matched {len(matched)}/{len(question.keywords)} keywords"
        if len(normalized) < self.min_length:
            feedback += "; below length target"

        return round_score(clamp(raw_score, 0.0, question.max_points)), feedback


class NumericRubricScorer(AbstractScorer):
    _number_pattern = re.compile(r"-?\d+(?:\.\d+)?")

    def __init__(self, target: float, tolerance: float, partial_credit: float = 0.5) -> None:
        super().__init__("numeric")
        self.target = target
        self.tolerance = tolerance
        self.partial_credit = partial_credit

    def _extract_number(self, response: str) -> float | None:
        match = self._number_pattern.search(response)
        if match is None:
            return None
        return float(match.group(0))

    def score_raw(self, question: RubricQuestion, response: str) -> tuple[float, str]:
        value = self._extract_number(response)
        if value is None:
            return 0.0, "no numeric answer"

        delta = abs(value - self.target)
        if delta <= self.tolerance:
            return round_score(question.max_points), "exact numeric match"
        if delta <= self.tolerance * 2:
            raw_score = question.max_points * self.partial_credit
            return round_score(raw_score), "close numeric match"
        return 0.0, f"outside tolerance by {round_score(delta):.4f}"


class WeightedRubricScorer(AbstractScorer):
    def __init__(self, components: Iterable[tuple[str, AbstractScorer, float]]) -> None:
        super().__init__("weighted")
        self.components = tuple(components)
        if not self.components:
            raise ValueError("WeightedRubricScorer requires at least one component")

    def _evaluate_components(self, question: RubricQuestion, response: str) -> list[tuple[str, float, str, float]]:
        rows: list[tuple[str, float, str, float]] = []
        for label, scorer, weight in self.components:
            raw_score, feedback = scorer.score_raw(question, response)
            rows.append((label, round_score(raw_score), feedback, weight))
        return rows

    def score_raw(self, question: RubricQuestion, response: str) -> tuple[float, str]:
        rows = self._evaluate_components(question, response)
        total_weight = sum(weight for _, _, _, weight in rows)
        weighted_ratio = sum(
            ((raw_score / question.max_points) if question.max_points else 0.0) * weight
            for _, raw_score, _, weight in rows
        ) / total_weight
        feedback = "; ".join(f"{label}={item_feedback}" for label, _, item_feedback, _ in rows)
        return round_score(question.max_points * weighted_ratio), feedback

    def build_result(self, question: RubricQuestion, response: str, **metadata: object) -> ScoreResult:
        rows = self._evaluate_components(question, response)
        total_weight = sum(weight for _, _, _, weight in rows)
        weighted_ratio = sum(
            ((raw_score / question.max_points) if question.max_points else 0.0) * weight
            for _, raw_score, _, weight in rows
        ) / total_weight
        raw_score = round_score(question.max_points * weighted_ratio)
        feedback = "; ".join(f"{label}={item_feedback}" for label, _, item_feedback, _ in rows)
        summary = ",".join(
            f"{label}:{raw_value:.4f}@{weight:.2f}"
            for label, raw_value, _, weight in rows
        )
        merged_metadata = {
            **metadata,
            "component_summary": summary,
            "component_count": len(rows),
        }
        return super().build_result(question, response, **merged_metadata).with_metadata(
            weighted_feedback=feedback
        )


@dataclass(frozen=True)
class SubmissionReport:
    student_id: str
    results: tuple[ScoreResult, ...]
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_results(
        cls,
        student_id: str,
        results: Iterable[ScoreResult],
        metadata: Mapping[str, object] | None = None,
    ) -> "SubmissionReport":
        return cls(
            student_id=student_id.strip(),
            results=tuple(results),
            metadata={str(key): str(value) for key, value in dict(metadata or {}).items()},
        )

    @property
    def total_weighted_score(self) -> float:
        return round_score(sum(result.weighted_score for result in self.results))

    @property
    def total_max_weighted(self) -> float:
        return round_score(sum(result.max_points * float(result.metadata.get("weight", 1.0)) for result in self.results))

    def average_ratio(self) -> float:
        denominator = sum(result.max_points * float(result.metadata.get("weight", 1.0)) for result in self.results)
        if denominator == 0:
            return 0.0
        return round_score(self.total_weighted_score / denominator)

    def render(self) -> str:
        details = ",".join(
            f"{result.question_id}:{result.weighted_score:.4f}"
            for result in self.results
        )
        return f"{self.student_id}|{self.total_weighted_score:.4f}|{self.average_ratio():.4f}|{details}"


class BatchRubricScorer:
    def __init__(
        self,
        questions: Iterable[RubricQuestion],
        scorers: Mapping[str, AbstractScorer],
        cohort_name: str = "default",
    ) -> None:
        self.questions = tuple(questions)
        self.scorers = dict(scorers)
        self.cohort_name = cohort_name.strip() or "default"

    def score_submission(self, student_id: str, responses: Mapping[str, str]) -> SubmissionReport:
        results: list[ScoreResult] = []
        for question in self.questions:
            scorer = self.scorers[question.question_id]
            response = str(responses.get(question.question_id, ""))
            result = scorer.build_result(
                question,
                response,
                student=student_id.strip(),
                cohort=self.cohort_name,
                weight=f"{question.weight:.4f}",
            )
            results.append(result)
        return SubmissionReport.from_results(
            student_id,
            results,
            {"cohort": self.cohort_name, "question_count": len(self.questions)},
        )

    def score_all(self, submissions: Iterable[tuple[str, Mapping[str, str]]]) -> list[SubmissionReport]:
        return [self.score_submission(student_id, answers) for student_id, answers in submissions]

    def average_ratio(self, reports: Iterable[SubmissionReport]) -> float:
        report_list = list(reports)
        if not report_list:
            return 0.0
        return round_score(sum(report.average_ratio() for report in report_list) / len(report_list))
