from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models import Element
from ui.object_index import ObjectIndex


def _element(guid: str, *, name: str = "Pipe 1", ifc_type: str = "IfcPipeSegment") -> Element:
    return Element(
        guid=guid,
        type=ifc_type,
        discipline="Plumbing",
        geom_ref=guid,
        name=name,
        system="Domestic Cold Water",
        psets={"Pset_PipeSegmentCommon": {"Reference": "P-100", "Status": True}},
        qtos={"Qto_PipeSegmentBaseQuantities": {"Length": 12.5}},
        type_psets={"Pset_ManufacturerTypeInformation": {"ModelReference": "ABC-42"}},
        type_qtos={"Qto_TypeBaseQuantities": {"NominalWeight": 1.2}},
        systems=["Domestic Cold Water"],
        system_group_names=["Domestic Cold Water"],
        ifc_meta={
            "elementKey": f"ek:{guid}",
            "modelKey": "model:demo",
            "source_file": "/models/project.ifc",
        },
    )


def test_object_index_rebuild_creates_flat_items_with_required_fields():
    index = ObjectIndex()
    elem = _element("0A1B2C")
    index.rebuild({"0A1B2C": elem}, source_path="/fallback/fallback.ifc", model_key="model:fallback")

    assert index.count == 1
    row = index.items[0]
    assert row.elementId == "ek:0A1B2C"
    assert row.globalId == "0A1B2C"
    assert row.name == "Pipe 1"
    assert row.type == "IfcPipeSegment"
    assert row.ifcType == "IfcPipeSegment"
    assert row.systemGroup == "Domestic Cold Water"
    assert row.sourceFileId == "model:demo"
    assert row.sourceFileName == "project.ifc"
    assert row.flattenedProperties["pset.Pset_PipeSegmentCommon.Reference"] == "P-100"
    assert row.flattenedProperties["pset.Pset_PipeSegmentCommon.Status"] == "true"
    assert row.flattenedProperties["qto.Qto_PipeSegmentBaseQuantities.Length"] == "12.5"
    assert row.flattenedProperties["type_pset.Pset_ManufacturerTypeInformation.ModelReference"] == "ABC-42"
    assert row.flattenedProperties["type_qto.Qto_TypeBaseQuantities.NominalWeight"] == "1.2"


def test_object_index_clear_and_fallback_source_fields():
    index = ObjectIndex()
    elem = _element("0X0Y0Z")
    elem.ifc_meta = {"elementKey": "ek:0X0Y0Z"}
    index.rebuild({"0X0Y0Z": elem}, source_path="/models/fallback-model.ifc", model_key="model:fallback")

    assert index.count == 1
    row = index.items[0]
    assert row.sourceFileId == "model:fallback"
    assert row.sourceFileName == "fallback-model.ifc"

    index.clear()
    assert index.count == 0
    assert index.items == []


def test_object_index_searchable_text_contains_global_and_flattened_fields():
    index = ObjectIndex()
    elem = _element("ABC123XYZ", name="Domestic Cold Water Segment")
    index.rebuild({"ABC123XYZ": elem}, source_path="/models/project.ifc", model_key="model:fallback")

    row = index.items[0]
    searchable = row.searchableText
    assert "domestic cold water segment" in searchable
    assert "abc123xyz" in searchable
    assert "pset.pset_pipesegmentcommon.reference" in searchable
    assert "p-100" in searchable
