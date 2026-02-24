from types import SimpleNamespace

from models import Element
from viewer.model_activation import activate_model_payload
from viewer.model_payload import ModelElementPayload, ModelMeshPayload, ModelPayload


def _payload(with_mesh: bool) -> ModelPayload:
    guid = "E1"
    element_ref = Element(guid=guid, type="IfcWall", discipline="arch", geom_ref=guid, name="Wall")
    elements = [
        ModelElementPayload(
            id=guid,
            globalId=guid,
            className="IfcWall",
            name="Wall",
            props={"discipline": "arch"},
        )
    ]
    meshes = []
    if with_mesh:
        meshes.append(
            ModelMeshPayload(
                id="mesh:E1",
                elementId=guid,
                vertices=(
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                ),
                indices=(0, 1, 2),
                aabb=(0.0, 1.0, 0.0, 1.0, 0.0, 0.0),
            )
        )
    return ModelPayload(
        sourcePath="dummy.ifc",
        repository=SimpleNamespace(path="dummy.ifc"),
        elementRefs={guid: element_ref},
        elements=elements,
        elementsParsed=len(elements),
        meshes=meshes,
        aabbs={guid: (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)},
        bboxWorld=(0.0, 1.0, 0.0, 1.0, 0.0, 0.0),
        warnings=tuple(),
    )


def test_activation_marks_viewer_loaded_and_calls_autofit_once():
    payload = _payload(with_mesh=True)
    auto_fit_calls = {"count": 0}

    result = activate_model_payload(
        payload,
        attach_meshes=lambda p: len(p.meshes),
        auto_fit_to_bbox=lambda _bbox: auto_fit_calls.__setitem__("count", auto_fit_calls["count"] + 1),
    )

    assert result.viewerModelLoaded is True
    assert result.elementsParsed > 0
    assert result.meshesRendered > 0
    assert result.warning is None
    assert result.autoFitCalls == 1
    assert auto_fit_calls["count"] == 1


def test_activation_explicit_warning_when_elements_exist_but_meshes_missing():
    payload = _payload(with_mesh=False)

    result = activate_model_payload(
        payload,
        attach_meshes=lambda _p: 0,
        auto_fit_to_bbox=lambda _bbox: None,
    )

    assert result.viewerModelLoaded is True
    assert result.elementsParsed > 0
    assert result.meshesRendered == 0
    assert result.warning is not None
    assert "0 meshes" in result.warning
    assert result.autoFitCalls == 0
