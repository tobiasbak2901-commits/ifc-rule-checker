from __future__ import annotations

import json
import zipfile
import datetime
import uuid
from typing import Dict, List
from xml.etree.ElementTree import Element, SubElement, tostring

from models import CandidateFix, Issue, Recommendation


def _xml_bytes(elem: Element) -> bytes:
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(elem, encoding="utf-8")


def export_bcfzip(
    out_path: str,
    ifc_filename: str,
    issues: List[Issue],
    recommendations: Dict[str, Recommendation],
) -> None:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        ver = Element("Version", {"VersionId": "2.1"})
        z.writestr("bcf.version", _xml_bytes(ver))

        for idx, issue in enumerate(issues, start=1):
            base_topic = issue.issue_id or f"issue-{idx}"
            if issue.viewpoint and issue.viewpoint.get("pair_index", 1) > 1:
                base_topic = f"{base_topic}:{issue.viewpoint['pair_index']}"
            topic_guid = _ensure_guid(base_topic, f"issue-{idx}")
            viewpoint_guid = _ensure_guid(f"{topic_guid}|viewpoint", f"viewpoint-{idx}")
            folder = f"{topic_guid}/"

            vis = Element("VisualizationInfo", {"Guid": viewpoint_guid})
            comps = SubElement(vis, "Components")
            sel = SubElement(comps, "Selection")
            if issue.guid_a:
                SubElement(sel, "Component", {"IfcGuid": issue.guid_a})
            if issue.guid_b:
                SubElement(sel, "Component", {"IfcGuid": issue.guid_b})

            persp = SubElement(vis, "PerspectiveCamera")
            cam = _camera_for_issue(issue)
            _write_vector(persp, "CameraViewPoint", cam["position"])
            _write_vector(persp, "CameraDirection", cam["direction"])
            _write_vector(persp, "CameraUpVector", cam["up"])
            SubElement(persp, "FieldOfView").text = str(cam["fov"])
            z.writestr(folder + "viewpoint.bcfv", _xml_bytes(vis))

            markup = Element("Markup")
            header = SubElement(markup, "Header")
            file_el = SubElement(header, "File")
            SubElement(file_el, "Filename").text = ifc_filename
            SubElement(file_el, "Date").text = now

            topic = SubElement(markup, "Topic", {"Guid": topic_guid})
            title = issue.title or issue.rule_id or "Issue"
            SubElement(topic, "Title").text = title
            SubElement(topic, "CreationDate").text = now
            SubElement(topic, "CreationAuthor").text = "AI/ResolutionEngine"
            SubElement(topic, "Priority").text = issue.severity or "Medium"
            SubElement(topic, "Status").text = "Open"
            if issue.movable_discipline:
                SubElement(topic, "AssignedTo").text = issue.movable_discipline

            rec = recommendations.get(issue.guid_a + "|" + issue.guid_b) if issue.guid_a and issue.guid_b else None
            clearance_text = f"{issue.clearance:.3f}" if issue.clearance is not None else "N/A"
            desc = [
                f"clearance: {clearance_text}",
                f"pA: {issue.p_a}",
                f"pB: {issue.p_b}",
            ]
            if rec:
                desc.append("recommendation: " + rec.explanation)
            else:
                desc.append("recommendation: NoSolution")

            SubElement(topic, "Description").text = "\n".join(desc)

            comment_guid = _ensure_guid(f"{topic_guid}|comment", f"comment-{idx}")
            comments = SubElement(markup, "Comment", {"Guid": comment_guid})
            SubElement(comments, "Date").text = now
            SubElement(comments, "Author").text = "AI/ResolutionEngine"
            if rec and _is_ok_fix(rec.top_fix):
                SubElement(comments, "Comment").text = _format_fix_comment(issue, rec.top_fix, rec.explanation)
            else:
                SubElement(comments, "Comment").text = _format_no_solution_comment(issue)
            SubElement(comments, "Viewpoint").text = viewpoint_guid

            viewpoints = SubElement(markup, "Viewpoints")
            vp = SubElement(viewpoints, "Viewpoint", {"Guid": viewpoint_guid})
            SubElement(vp, "Viewpoint").text = "viewpoint.bcfv"

            z.writestr(folder + "markup.bcf", _xml_bytes(markup))


def _is_ok_fix(fix: CandidateFix) -> bool:
    return fix.min_clearance is not None and fix.min_clearance >= 0


def _format_fix_comment(issue: Issue, fix: CandidateFix, explanation: str) -> str:
    before = issue.clearance
    after = fix.params.get("clearance_after_m")
    before_text = f"{before:.3f} m" if before is not None else "N/A"
    after_text = f"{after:.3f} m" if after is not None else "N/A"
    min_clear = fix.min_clearance
    min_clear_text = f"{min_clear:.3f} m" if min_clear is not None else "N/A"
    payload = {
        "action": fix.action,
        "guid": fix.params.get("guid"),
        "vector_m": fix.params.get("vector_m"),
        "vector_mm": fix.params.get("vector_mm"),
        "solves": fix.solves,
        "creates": fix.creates,
        "score": fix.score,
    }
    lines = [
        "Decision: Recommended OK fix",
        f"Effect: solves={fix.solves}, creates={fix.creates}, minClearance={min_clear_text}",
        f"Clearance: {before_text} -> {after_text}",
        f"Note: {explanation}",
        f"Payload: {json.dumps(payload)}",
    ]
    return "\n".join(lines)


def _format_no_solution_comment(issue: Issue) -> str:
    clearance_text = f"{issue.clearance:.3f} m" if issue.clearance is not None else "N/A"
    if issue.guid_a and issue.guid_b:
        if issue.p_a and issue.p_b:
            reason = "No feasible fix found."
        else:
            reason = "Missing geometry for one or both elements."
    else:
        reason = "Missing element GUID(s)."
    lines = [
        "Decision: NoSolution",
        f"Clearance: {clearance_text}",
        f"Reason: {reason}",
    ]
    return "\n".join(lines)


def _ensure_guid(raw: str | None, fallback: str) -> str:
    if raw:
        try:
            return str(uuid.UUID(raw))
        except (ValueError, AttributeError, TypeError):
            return str(uuid.uuid5(uuid.NAMESPACE_URL, str(raw)))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, fallback))


def _write_vector(parent: Element, tag: str, vec) -> None:
    elem = SubElement(parent, tag)
    SubElement(elem, "X").text = f"{vec[0]:.3f}"
    SubElement(elem, "Y").text = f"{vec[1]:.3f}"
    SubElement(elem, "Z").text = f"{vec[2]:.3f}"


def _camera_for_issue(issue: Issue) -> Dict[str, object]:
    if issue.viewpoint:
        cam = issue.viewpoint.get("camera")
        if cam and cam.get("position") and cam.get("direction") and cam.get("up"):
            return {
                "position": cam["position"],
                "direction": cam["direction"],
                "up": cam["up"],
                "fov": 60,
            }
    center = None
    if issue.clash_center:
        center = issue.clash_center
    elif issue.p_a and issue.p_b:
        center = (
            (issue.p_a[0] + issue.p_b[0]) / 2.0,
            (issue.p_a[1] + issue.p_b[1]) / 2.0,
            (issue.p_a[2] + issue.p_b[2]) / 2.0,
        )
    if center is None:
        return {"position": (0.0, 0.0, 10.0), "direction": (0.0, 0.0, -1.0), "up": (0.0, 1.0, 0.0), "fov": 60}
    offset = 5.0
    if issue.p_a and issue.p_b:
        dx = issue.p_a[0] - issue.p_b[0]
        dy = issue.p_a[1] - issue.p_b[1]
        dz = issue.p_a[2] - issue.p_b[2]
        dist = (dx * dx + dy * dy + dz * dz) ** 0.5
        offset = max(2.0, dist * 4.0)
    return {
        "position": (center[0], center[1], center[2] + offset),
        "direction": (0.0, 0.0, -1.0),
        "up": (0.0, 1.0, 0.0),
        "fov": 60,
    }
