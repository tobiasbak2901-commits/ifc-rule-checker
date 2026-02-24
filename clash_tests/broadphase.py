from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from geometry import aabb_expand, aabb_intersects

from .proxy_builder import GeometryProxy

AABB = Tuple[float, float, float, float, float, float]
CellKey = Tuple[int, int, int]


@dataclass(frozen=True)
class CandidatePair:
    aKey: str
    bKey: str
    aProxy: GeometryProxy
    bProxy: GeometryProxy


class UniformGridIndex:
    def __init__(self, *, cell_size_m: float = 2.0):
        self.cell_size_m = max(0.05, float(cell_size_m or 2.0))
        self._buckets: Dict[CellKey, List[GeometryProxy]] = {}

    def insert(self, proxy: GeometryProxy) -> None:
        for key in _aabb_cells(_proxy_aabb(proxy), self.cell_size_m):
            self._buckets.setdefault(key, []).append(proxy)

    def query(self, aabb: AABB) -> Iterable[GeometryProxy]:
        seen_ids: Set[str] = set()
        for key in _aabb_cells(aabb, self.cell_size_m):
            for proxy in self._buckets.get(key, []):
                proxy_id = str(proxy.elementId or "")
                if proxy_id in seen_ids:
                    continue
                seen_ids.add(proxy_id)
                yield proxy


def broadphase(
    proxies_a: Iterable[GeometryProxy],
    proxies_b: Iterable[GeometryProxy],
    *,
    cell_size_m: float = 2.0,
    padding_m: float = 0.0,
    same_set: bool = False,
    batch_size: int = 512,
    on_batch: Optional[Callable[[int, int], None]] = None,
) -> List[CandidatePair]:
    left = [p for p in list(proxies_a or []) if p is not None]
    right = [p for p in list(proxies_b or []) if p is not None]
    if not left or not right:
        return []

    pad = max(0.0, float(padding_m or 0.0))
    grid = UniformGridIndex(cell_size_m=cell_size_m)
    for proxy in right:
        grid.insert(proxy)

    out: List[CandidatePair] = []
    seen_pairs: Set[Tuple[str, str]] = set()
    total = len(left)
    step = max(64, int(batch_size or 512))

    for idx, proxy_a in enumerate(left, start=1):
        query_box = aabb_expand(_proxy_aabb(proxy_a), pad)
        for proxy_b in grid.query(query_box):
            id_a = str(proxy_a.elementId or "")
            id_b = str(proxy_b.elementId or "")
            if not id_a or not id_b:
                continue
            if same_set and id_a == id_b:
                continue
            if same_set:
                ordered = tuple(sorted((id_a, id_b)))
            else:
                ordered = (id_a, id_b)
            if ordered in seen_pairs:
                continue
            if not aabb_intersects(query_box, _proxy_aabb(proxy_b)):
                continue
            seen_pairs.add(ordered)
            out.append(
                CandidatePair(
                    aKey=str(proxy_a.elementKey or id_a),
                    bKey=str(proxy_b.elementKey or id_b),
                    aProxy=proxy_a,
                    bProxy=proxy_b,
                )
            )
        if on_batch is not None and (idx % step == 0 or idx == total):
            try:
                on_batch(int(idx), int(total))
            except Exception:
                pass
    return out


def _proxy_aabb(proxy: GeometryProxy) -> AABB:
    return (
        float(proxy.aabb.min[0]),
        float(proxy.aabb.min[1]),
        float(proxy.aabb.min[2]),
        float(proxy.aabb.max[0]),
        float(proxy.aabb.max[1]),
        float(proxy.aabb.max[2]),
    )


def _aabb_cells(aabb: AABB, cell_size: float) -> Iterable[CellKey]:
    min_x, min_y, min_z, max_x, max_y, max_z = [float(v) for v in aabb]
    ix0 = int(math.floor(min_x / cell_size))
    iy0 = int(math.floor(min_y / cell_size))
    iz0 = int(math.floor(min_z / cell_size))
    ix1 = int(math.floor(max_x / cell_size))
    iy1 = int(math.floor(max_y / cell_size))
    iz1 = int(math.floor(max_z / cell_size))
    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            for iz in range(iz0, iz1 + 1):
                yield (ix, iy, iz)
