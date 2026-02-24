from __future__ import annotations

import os
import zipfile
from typing import Dict, List, Optional, Tuple
from xml.etree.ElementTree import Element, fromstring

from models import Issue


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _find(elem: Element, tag: str) -> Optional[Element]:
    wanted = tag.lower()
    for child in elem:
        if _local(child.tag).lower() == wanted:
            return child
    return None


def _findall(elem: Element, tag: str) -> List[Element]:
    wanted = tag.lower()
    return [child for child in elem if _local(child.tag).lower() == wanted]


def _text(elem: Element, tag: str) -> Optional[str]:
    child = _find(elem, tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_markup(root: Element, load_viewpoint, load_snapshot) -> List[Issue]:
    issues: List[Issue] = []

    topic = _find(root, "Topic")
    if topic is None:
        return issues
    severity = _text(topic, "Priority") or _text(topic, "Severity") or "Medium"
    title = _text(topic, "Title") or "BCF"
    description = _text(topic, "Description")
    topic_guid = topic.attrib.get("Guid") or "issue"

    viewpoints = _find(topic, "Viewpoints")
    if viewpoints is None:
        viewpoints_list = []
    else:
        viewpoints_list = _findall(viewpoints, "Viewpoint")

    if not viewpoints_list:
        issues.append(
            Issue(
                guid_a="",
                guid_b="",
                rule_id=title,
                severity=severity,
                clearance=0.0,
                p_a=None,
                p_b=None,
                direction=None,
                viewpoint=None,
                clash_center=None,
                issue_id=topic_guid,
                title=title,
                bcf_description=description,
                bcf_comments=_parse_comments(root),
            )
        )
        return issues

    for vp in viewpoints_list:
        vref = _text(vp, "Viewpoint")
        snapshot = _text(vp, "Snapshot")
        guids: List[str] = []
        camera = None
        if vref and load_viewpoint:
            try:
                vroot = load_viewpoint(vref)
                camera = _parse_viewpoint_camera(vroot)
                comps = _find(vroot, "Components")
                sel = _find(comps, "Selection") if comps is not None else None
                if sel is not None:
                    for comp in _findall(sel, "Component"):
                        guid = comp.attrib.get("IfcGuid")
                        if guid and guid not in guids:
                            guids.append(guid)
            except Exception:
                pass
        snapshot_bytes = None
        snapshot_mime = None
        if snapshot and load_snapshot:
            try:
                snapshot_bytes = load_snapshot(snapshot)
                snapshot_mime = _guess_image_mime(snapshot)
            except Exception:
                snapshot_bytes = None

        if len(guids) >= 2:
            pairs = []
            for i in range(len(guids) - 1):
                for j in range(i + 1, len(guids)):
                    pairs.append((guids[i], guids[j]))
        else:
            pairs = [(guids[0] if guids else "", guids[1] if len(guids) > 1 else "")]

        for idx, (guid_a, guid_b) in enumerate(pairs, start=1):
            issues.append(
                Issue(
                    guid_a=guid_a,
                    guid_b=guid_b,
                    rule_id=title,
                    severity=severity,
                    clearance=0.0,
                    p_a=None,
                    p_b=None,
                    direction=None,
                    viewpoint={
                        "viewpoint_path": vref,
                        "snapshot_path": snapshot,
                        "pair_index": idx,
                        "camera": camera,
                    } if vref or snapshot else None,
                    clash_center=None,
                    issue_id=topic_guid,
                    title=title,
                    bcf_description=description,
                    bcf_comments=_parse_comments(root),
                    snapshot_bytes=snapshot_bytes,
                    snapshot_mime=snapshot_mime,
                )
            )
    return issues


def _parse_viewpoint_camera(root: Element) -> Optional[Dict]:
    perspective = _find(root, "PerspectiveCamera")
    orthogonal = _find(root, "OrthogonalCamera")
    cam = perspective or orthogonal
    if cam is None:
        return None
    view_point = _parse_vector(_find(cam, "CameraViewPoint"))
    direction = _parse_vector(_find(cam, "CameraDirection"))
    up = _parse_vector(_find(cam, "CameraUpVector"))
    if view_point is None or direction is None or up is None:
        return None
    data: Dict[str, object] = {
        "type": "perspective" if perspective is not None else "orthogonal",
        "position": view_point,
        "direction": direction,
        "up": up,
    }
    if orthogonal is not None:
        scale = _text(orthogonal, "ViewToWorldScale")
        if scale:
            try:
                data["scale"] = float(scale)
            except ValueError:
                pass
    return data


def _parse_vector(elem: Optional[Element]) -> Optional[Tuple[float, float, float]]:
    if elem is None:
        return None
    x = _text(elem, "X")
    y = _text(elem, "Y")
    z = _text(elem, "Z")
    if x is None or y is None or z is None:
        return None
    try:
        return (float(x), float(y), float(z))
    except ValueError:
        return None


def import_bcf(path: str) -> List[Issue]:
    if not zipfile.is_zipfile(path):
        with open(path, "rb") as f:
            data = f.read()
        root = fromstring(data)

        base_dir = os.path.dirname(path)

        def _load_viewpoint(vref: str):
            vp_path = os.path.join(base_dir, vref)
            with open(vp_path, "rb") as vf:
                return fromstring(vf.read())

        def _load_snapshot(sref: str):
            spath = os.path.join(base_dir, sref)
            with open(spath, "rb") as sf:
                return sf.read()

        issues = _parse_markup(root, _load_viewpoint, _load_snapshot)
        if not issues:
            raise ValueError("BCF file missing Topic or Viewpoints")
        return issues

    issues: List[Issue] = []
    with zipfile.ZipFile(path, "r") as z:
        for name in z.namelist():
            if not name.endswith("markup.bcf"):
                continue
            data = z.read(name)
            root = fromstring(data)
            topic = _find(root, "Topic")
            if topic is None:
                continue
            topic_guid = topic.attrib.get("Guid") or name.split("/")[0]

            def _load_viewpoint(vref: str):
                vdata = z.read(name.replace("markup.bcf", vref))
                return fromstring(vdata)

            def _load_snapshot(sref: str):
                return z.read(name.replace("markup.bcf", sref))

            parsed = _parse_markup(root, _load_viewpoint, _load_snapshot)
            for issue in parsed:
                if issue.issue_id is None:
                    issue.issue_id = topic_guid
                if issue.viewpoint is None:
                    issue.viewpoint = {"bcf_path": name}
                else:
                    issue.viewpoint["bcf_path"] = name
                issues.append(issue)

    return issues


def _parse_comments(root: Element) -> List[str]:
    comments: List[str] = []
    for comment in _findall(root, "Comment"):
        body = _text(comment, "Comment") or ""
        author = _text(comment, "Author") or ""
        date = _text(comment, "Date") or ""
        parts = [p for p in [author, date, body] if p]
        if parts:
            comments.append(" | ".join(parts))
    return comments


def _guess_image_mime(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"
