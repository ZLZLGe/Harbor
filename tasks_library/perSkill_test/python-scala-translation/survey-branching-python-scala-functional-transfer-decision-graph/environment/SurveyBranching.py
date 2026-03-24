from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Mapping


Answers = Mapping[str, Any]
Predicate = Callable[[Answers], "PredicateResult"]


def _stable_dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def _render_status(matched: bool | None, missing_answers: tuple[str, ...]) -> str:
    if matched is True:
        return "matched"
    if matched is False:
        return "skipped"
    if missing_answers:
        return f"pending:{','.join(missing_answers)}"
    return "pending"


@dataclass(frozen=True)
class PredicateResult:
    matched: bool | None
    missing_answers: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class ExplanationStep:
    node_id: str
    branch_label: str
    matched: bool | None
    detail: str
    missing_answers: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionResult:
    segment: str | None
    rationale: str | None
    missing_answers: tuple[str, ...]
    path: tuple[ExplanationStep, ...]

    def is_resolved(self) -> bool:
        return self.segment is not None and not self.missing_answers

    def explanation_path(self) -> tuple[str, ...]:
        prefix = tuple(
            f"{step.node_id}.{step.branch_label}:{_render_status(step.matched, step.missing_answers)}"
            for step in self.path
        )
        if self.segment is not None:
            return prefix + (f"segment:{self.segment}",)
        if self.missing_answers:
            return prefix + (f"pending:{','.join(self.missing_answers)}",)
        return prefix + ("unresolved",)


@dataclass(frozen=True)
class OutcomeNode:
    segment: str
    rationale: str


@dataclass(frozen=True)
class BranchCase:
    label: str
    predicate: Predicate
    next_node: "SurveyNode"


@dataclass(frozen=True)
class BranchNode:
    node_id: str
    cases: tuple[BranchCase, ...]
    default_next: "SurveyNode | None" = None
    default_label: str = "default"


SurveyNode = OutcomeNode | BranchNode


class SurveyBranching:
    @staticmethod
    def _missing(question: str, detail: str) -> PredicateResult:
        return PredicateResult(None, (question,), detail)

    @staticmethod
    def answer_equals(question: str, expected: Any) -> Predicate:
        def predicate(answers: Answers) -> PredicateResult:
            if question not in answers or answers[question] is None:
                return SurveyBranching._missing(question, f"{question} missing")
            return PredicateResult(answers[question] == expected, (), f"{question} == {expected}")

        return predicate

    @staticmethod
    def answer_in(question: str, choices: set[str] | frozenset[str]) -> Predicate:
        normalized_choices = frozenset(choices)
        choice_text = ",".join(sorted(normalized_choices))

        def predicate(answers: Answers) -> PredicateResult:
            if question not in answers or answers[question] is None:
                return SurveyBranching._missing(question, f"{question} missing")
            actual = answers[question]
            return PredicateResult(actual in normalized_choices, (), f"{question} in [{choice_text}]")

        return predicate

    @staticmethod
    def numeric_at_least(question: str, threshold: Decimal | int | str) -> Predicate:
        threshold_value = Decimal(str(threshold))

        def predicate(answers: Answers) -> PredicateResult:
            if question not in answers or answers[question] is None:
                return SurveyBranching._missing(question, f"{question} missing")
            try:
                value = Decimal(str(answers[question]))
            except (InvalidOperation, ValueError, TypeError):
                return PredicateResult(False, (), f"{question} invalid-number")
            return PredicateResult(value >= threshold_value, (), f"{question} >= {threshold_value}")

        return predicate

    @staticmethod
    def all_of(*predicates: Predicate) -> Predicate:
        def predicate(answers: Answers) -> PredicateResult:
            checks = tuple(item(answers) for item in predicates)
            if any(check.matched is False for check in checks):
                return PredicateResult(False, (), "allOf")
            missing_answers = _stable_dedupe(
                missing for check in checks if check.matched is None for missing in check.missing_answers
            )
            if missing_answers:
                return PredicateResult(None, missing_answers, "allOf")
            return PredicateResult(True, (), "allOf")

        return predicate

    @staticmethod
    def any_of(*predicates: Predicate) -> Predicate:
        def predicate(answers: Answers) -> PredicateResult:
            checks = tuple(item(answers) for item in predicates)
            if any(check.matched is True for check in checks):
                return PredicateResult(True, (), "anyOf")
            missing_answers = _stable_dedupe(
                missing for check in checks if check.matched is None for missing in check.missing_answers
            )
            if missing_answers:
                return PredicateResult(None, missing_answers, "anyOf")
            return PredicateResult(False, (), "anyOf")

        return predicate

    @staticmethod
    def evaluate(node: SurveyNode, answers: Answers) -> DecisionResult:
        return SurveyBranching._evaluate(node, answers, ())

    @staticmethod
    def _evaluate(
        node: SurveyNode,
        answers: Answers,
        path: tuple[ExplanationStep, ...],
    ) -> DecisionResult:
        if isinstance(node, OutcomeNode):
            return DecisionResult(node.segment, node.rationale, (), path)

        attempted_steps: list[ExplanationStep] = []
        pending_missing: list[str] = []

        for branch_case in node.cases:
            check = branch_case.predicate(answers)
            step = ExplanationStep(
                node_id=node.node_id,
                branch_label=branch_case.label,
                matched=check.matched,
                detail=check.detail,
                missing_answers=check.missing_answers,
            )
            attempted_steps.append(step)
            if check.matched is True:
                return SurveyBranching._evaluate(branch_case.next_node, answers, path + tuple(attempted_steps))
            if check.matched is None:
                pending_missing.extend(check.missing_answers)

        if pending_missing:
            return DecisionResult(
                segment=None,
                rationale=None,
                missing_answers=_stable_dedupe(pending_missing),
                path=path + tuple(attempted_steps),
            )

        if node.default_next is not None:
            default_step = ExplanationStep(
                node_id=node.node_id,
                branch_label=node.default_label,
                matched=True,
                detail="default",
            )
            return SurveyBranching._evaluate(
                node.default_next,
                answers,
                path + tuple(attempted_steps) + (default_step,),
            )

        return DecisionResult(
            segment=None,
            rationale=None,
            missing_answers=(),
            path=path + tuple(attempted_steps),
        )

    @staticmethod
    def reachable_segments(node: SurveyNode) -> tuple[str, ...]:
        if isinstance(node, OutcomeNode):
            return (node.segment,)

        collected: list[str] = []
        for branch_case in node.cases:
            collected.extend(SurveyBranching.reachable_segments(branch_case.next_node))
        if node.default_next is not None:
            collected.extend(SurveyBranching.reachable_segments(node.default_next))
        return _stable_dedupe(collected)

    @staticmethod
    def render_explanation(result: DecisionResult) -> str:
        return " -> ".join(result.explanation_path())
