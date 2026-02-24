from __future__ import annotations

import math
from typing import Dict, Optional

from models import CandidateFix, Issue, SimResult


def format_fix_description(
    fix: CandidateFix,
    sim: SimResult,
    issue: Issue,
    element_meta: Dict[str, Optional[object]],
) -> Dict[str, str]:
    dx = float(fix.params.get("dx", 0.0))
    dy = float(fix.params.get("dy", 0.0))
    dz = float(fix.params.get("dz", 0.0))
    move_m = math.sqrt(dx * dx + dy * dy + dz * dz)

    direction = _direction_label(dx, dy, dz)
    element_label = _element_label(element_meta)

    title_line = f"Flyt {element_label} {direction} {move_m:.3f} m"
    min_clear = fix.min_clearance if fix.min_clearance is not None else None
    min_clear_text = _clearance_text(min_clear)

    effect_line = (
        f"Effekt: løser {sim.solves}, skaber {sim.creates}, minClearance {min_clear_text}"
    )

    why_move = element_meta.get("why_move") or "Valgt ud fra prioritet/protection."
    why_path = element_meta.get("why_path") or _why_line(sim.solves, sim.creates, min_clear)
    reason_codes = list(element_meta.get("reason_codes") or [])
    debug_line = (
        f"debug: dx={dx:.4f} dy={dy:.4f} dz={dz:.4f} score={sim.score:.2f} "
        f"issue={issue.issue_id or ''}"
    )
    if reason_codes:
        debug_line += f" reasons={','.join(reason_codes)}"

    return {
        "titleLine": title_line,
        "effectLine": effect_line,
        "whyMoveLine": why_move,
        "whyPathLine": why_path,
        "whyLine": f"{why_move} | {why_path}",
        "debugLine": debug_line,
        "reasonCodes": reason_codes,
    }


def _direction_label(dx: float, dy: float, dz: float) -> str:
    ax, ay, az = abs(dx), abs(dy), abs(dz)
    if ax == 0 and ay == 0 and az == 0:
        return "+X"
    if az > max(ax, ay):
        return "+Z" if dz >= 0 else "-Z"
    if ax >= ay:
        return "Ø" if dx >= 0 else "V"
    return "N" if dy >= 0 else "S"


def _element_label(meta: Dict[str, Optional[object]]) -> str:
    elem_type = str(meta.get("type") or "Element")
    discipline = meta.get("discipline")
    system_name = meta.get("system")
    diameter_mm = meta.get("diameter_mm")
    parts = [elem_type]
    extra = []
    if discipline:
        extra.append(str(discipline))
    if system_name:
        extra.append(str(system_name))
    if diameter_mm is not None:
        extra.append(f"Ø{float(diameter_mm):.0f} mm")
    if extra:
        parts.append(f"({', '.join(extra)})")
    return " ".join(parts)


def _clearance_text(min_clear_m: Optional[float]) -> str:
    if min_clear_m is None:
        return "N/A"
    sign = "+" if min_clear_m >= 0 else "-"
    return f"{sign}{abs(min_clear_m):.3f} m"


def _why_line(solves: int, creates: int, min_clear_m: Optional[float]) -> str:
    if solves >= 1 and creates == 0 and (min_clear_m is None or min_clear_m >= 0):
        return "Fjerner clash uden at skabe nye."
    if solves >= 1 and creates > 0:
        return "Fjerner clash, men skaber nye."
    if min_clear_m is not None and min_clear_m < 0:
        return "Forflytning er for lille; clash består."
    return "Effekten er usikker; kræver manuel vurdering."
