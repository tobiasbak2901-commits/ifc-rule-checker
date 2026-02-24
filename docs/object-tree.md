# Object Tree

## Views

Object Tree now has two levels of tabs:

- Top tabs:
  - `AI Views` (default)
  - `By File`
- Inner tabs:
  - `Tree`
  - `Properties`

`Tree` only shows search + hierarchy. `Properties` only shows favorites/property groups and the property table for the selected element.

## Data Model

Tree rendering is built from a dedicated node model in `ui/panels/object_tree_views.py`:

- `id`: stable node id
- `label`: display text
- `icon`: optional text icon marker
- `count`: optional aggregate count
- `children`: nested nodes
- `element_ids`: IFC GlobalIds represented by the node

All selection from tree nodes is driven by `element_ids`.

## AI Views

`AI Views` is task-oriented and built from IFC elements + clash issues:

- `Clashing elements (count)`
  - `Active test: <name>`
  - `Top groups` (from clash diagnostics group metadata if available)
  - `Elements`
- `Unclassified elements (count)`
  - Elements missing classification and/or system/type context
- `High-risk systems (count)`
  - Grouped by system first, then discipline, then type bucket fallback
  - Sorted by number of clashes descending
- `Recently selected (count)`
  - Last 10 selected elements

### Count Rules

- `Clashing elements`: unique element ids involved in issues.
- `Unclassified elements`: elements where classification is unknown/missing, or system/type is missing.
- `High-risk systems`: buckets ranked by number of clash issues touching that bucket.
- `Recently selected`: deduped recency list, capped at 10.

## By File

Hierarchy:

- `File`
  - `System` or `Discipline` group
    - Friendly `Item Type`
      - Elements

## IFC Type Alias Mapping

Friendly labels are centralized in `ui/panels/object_tree_views.py` (`_FRIENDLY_ITEM_TYPE_ALIASES`).

Current aliases include:

- `IfcFlowSegment` -> `MEP Segments`
- `IfcPipeSegment` -> `Pipes`
- `IfcDuctSegment` -> `Ducts`
- `IfcCableCarrierSegment` -> `Cable Trays`
- `IfcFlowFitting` -> `Fittings`
- `IfcValve` -> `Valves`
- `IfcPump`, `IfcFan` -> `Equipment`
- `IfcWall` -> `Walls`
- `IfcSlab` -> `Slabs`

Fallback is the original IFC type string.

To add new aliases, extend `_FRIENDLY_ITEM_TYPE_ALIASES`.
