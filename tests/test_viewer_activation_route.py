from types import SimpleNamespace

from models import Element
from viewer.model_activation import ModelActivationStore
from viewer.model_payload import ModelElementPayload, ModelMeshPayload, ModelPayload


def _payload(with_mesh: bool) -> ModelPayload:
    guid = "E1"
    element_ref = Element(guid=guid, type="IfcPipeSegment", discipline="mep", geom_ref=guid, name="Pipe")
    elements = [
        ModelElementPayload(
            id=guid,
            globalId=guid,
            className="IfcPipeSegment",
            name="Pipe",
            props={"discipline": "mep"},
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
        sourcePath="known.ifc",
        repository=SimpleNamespace(path="known.ifc"),
        elementRefs={guid: element_ref},
        elements=elements,
        elementsParsed=len(elements),
        meshes=meshes,
        aabbs={guid: (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)},
        bboxWorld=(0.0, 1.0, 0.0, 1.0, 0.0, 0.0),
        warnings=tuple(),
    )


class _ActivationRouteHarness:
    def __init__(self):
        self.debug_cube_visible = True
        self.meshes_rendered = 0
        self.warning = None
        self.store = ModelActivationStore(self._activate_once)

    def _activate_once(self, payload: ModelPayload, *, sourceTag: str, token: int):
        del sourceTag, token
        self.meshes_rendered = int(len(payload.meshes))
        self.warning = None
        if int(payload.elementsParsed) > 0 and self.meshes_rendered == 0:
            self.warning = "Parsed but 0 meshes - triangulation/geometry pipeline missing."


def test_activation_route_counts_once_per_load_with_geometry():
    harness = _ActivationRouteHarness()
    payload = _payload(with_mesh=True)
    before = harness.store.snapshot().activationCount
    harness.store.activateModel(payload, sourceTag="test_known_ifc")
    after = harness.store.snapshot().activationCount

    assert after == before + 1
    assert harness.meshes_rendered > 0 or harness.warning is not None
    assert harness.debug_cube_visible is True


def test_activation_route_reports_warning_when_parsed_without_meshes():
    harness = _ActivationRouteHarness()
    payload = _payload(with_mesh=False)
    harness.store.activateModel(payload, sourceTag="test_known_ifc_no_mesh")

    assert harness.meshes_rendered == 0
    assert harness.warning is not None
    assert "Parsed but 0 meshes" in harness.warning
    assert harness.debug_cube_visible is True


def test_store_debounces_duplicate_activation_for_same_payload():
    harness = _ActivationRouteHarness()
    payload = _payload(with_mesh=True)
    harness.store.activateModel(payload, sourceTag="first_load")
    first_count = harness.store.snapshot().activationCount

    harness.store.activateModel(payload, sourceTag="duplicate_load")
    second_count = harness.store.snapshot().activationCount

    assert second_count == first_count


def test_store_ignores_reentrant_duplicate_for_same_payload():
    payload = _payload(with_mesh=True)
    store = None

    def _callback(model_payload: ModelPayload, *, sourceTag: str, token: int):
        del sourceTag, token
        store.activateModel(model_payload, sourceTag="duplicate_during_activation")

    store = ModelActivationStore(_callback, debounce_ms=0)
    store.activateModel(payload, sourceTag="initial")

    snapshot = store.snapshot()
    assert snapshot.activationCount == 1
