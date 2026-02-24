from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class FallbackTrial:
    element_id: str
    dx_mm: float
    dy_mm: float
    dz_mm: float
    move_distance_mm: float
    resolved_clashes: int
    min_clearance_improvement_mm: float
    creates_new_clash: bool
    violates_constraints: bool
    score: float


class FixGeneratorFallback:
    XY_STEPS_MM: Tuple[float, ...] = (25.0, 50.0, 75.0)

    @staticmethod
    def score_trial(
        *,
        resolved_clashes: int,
        min_clearance_improvement_mm: float,
        move_distance_mm: float,
        creates_new_clash: bool,
        violates_constraints: bool,
    ) -> float:
        improvement = max(0.0, min(float(min_clearance_improvement_mm), 2000.0))
        move_penalty = max(0.0, float(move_distance_mm)) / 10.0
        return (
            100.0 * max(0, int(resolved_clashes))
            + 10.0 * (improvement / 10.0)
            - 1.0 * move_penalty
            - 50.0 * (1.0 if bool(creates_new_clash) else 0.0)
            - 20.0 * (1.0 if bool(violates_constraints) else 0.0)
        )

    @classmethod
    def candidate_offsets_mm(cls, *, z_move_allowed: bool = False) -> List[Tuple[float, float, float]]:
        out: List[Tuple[float, float, float]] = []
        seen = set()
        steps = list(cls.XY_STEPS_MM)
        for sx in steps:
            for dx in (sx, -sx):
                for dy in (0.0, sx, -sx):
                    candidate = (float(dx), float(dy), 0.0)
                    if candidate not in seen:
                        out.append(candidate)
                        seen.add(candidate)
        for sy in steps:
            for dy in (sy, -sy):
                candidate = (0.0, float(dy), 0.0)
                if candidate not in seen:
                    out.append(candidate)
                    seen.add(candidate)
        if z_move_allowed:
            for sz in steps:
                for dz in (sz, -sz):
                    candidate = (0.0, 0.0, float(dz))
                    if candidate not in seen:
                        out.append(candidate)
                        seen.add(candidate)
        return out

    @staticmethod
    def move_distance_mm(dx_mm: float, dy_mm: float, dz_mm: float) -> float:
        return sqrt(float(dx_mm) ** 2 + float(dy_mm) ** 2 + float(dz_mm) ** 2)

    @staticmethod
    def rank_trials(trials: Iterable[FallbackTrial]) -> List[FallbackTrial]:
        return sorted(
            list(trials),
            key=lambda t: (
                -float(t.score),
                bool(t.creates_new_clash),
                bool(t.violates_constraints),
                float(t.move_distance_mm),
                str(t.element_id),
                float(t.dx_mm),
                float(t.dy_mm),
                float(t.dz_mm),
            ),
        )

    @classmethod
    def build_trials(
        cls,
        *,
        element_id: str,
        offsets_mm: Sequence[Tuple[float, float, float]],
        evaluator,
    ) -> List[FallbackTrial]:
        trials: List[FallbackTrial] = []
        for dx_mm, dy_mm, dz_mm in offsets_mm:
            metrics = dict(evaluator(float(dx_mm), float(dy_mm), float(dz_mm)) or {})
            resolved = int(metrics.get("resolved_clashes") or 0)
            improvement_mm = float(metrics.get("min_clearance_improvement_mm") or 0.0)
            creates_new = bool(metrics.get("creates_new_clash"))
            violates = bool(metrics.get("violates_constraints"))
            distance_mm = cls.move_distance_mm(dx_mm, dy_mm, dz_mm)
            trials.append(
                FallbackTrial(
                    element_id=str(element_id),
                    dx_mm=float(dx_mm),
                    dy_mm=float(dy_mm),
                    dz_mm=float(dz_mm),
                    move_distance_mm=float(distance_mm),
                    resolved_clashes=resolved,
                    min_clearance_improvement_mm=improvement_mm,
                    creates_new_clash=creates_new,
                    violates_constraints=violates,
                    score=cls.score_trial(
                        resolved_clashes=resolved,
                        min_clearance_improvement_mm=improvement_mm,
                        move_distance_mm=distance_mm,
                        creates_new_clash=creates_new,
                        violates_constraints=violates,
                    ),
                )
            )
        return trials
