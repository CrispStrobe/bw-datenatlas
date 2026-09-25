#!/usr/bin/env python3
"""Which municipality of Baden-Württemberg a coordinate lies in.

The atlas asked this question with a bounding box for a long time, and a rectangle drawn
round Baden-Württemberg contains Neu-Ulm, Günzburg, Viernheim, Germersheim and Wörth.
Thirty-one institutions outside the state were published as if they were in it. The
boundaries are already in the build; this asks them instead.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / 'docs/data/geometry.json'


class Municipalities:
    """The 1103 municipal boundaries, prepared once for repeated point lookups."""

    def __init__(self, path: Path | None = None) -> None:
        features = json.loads((path or GEOMETRY).read_text(encoding='utf-8'))['municipalities']
        self.prepared = []
        for feature in features:
            rings = self._rings(feature['geometry'])
            xs = [x for ring in rings for x, _ in ring]
            ys = [y for ring in rings for _, y in ring]
            self.prepared.append((min(xs), min(ys), max(xs), max(ys), rings,
                                  feature['properties']))

    @staticmethod
    def _rings(geometry: dict) -> list:
        if geometry['type'] == 'Polygon':
            return geometry['coordinates']
        return [ring for polygon in geometry['coordinates'] for ring in polygon]

    @staticmethod
    def _inside(rings: list, x: float, y: float) -> bool:
        hit = False
        for ring in rings:
            for i in range(len(ring)):
                x1, y1 = ring[i]
                x2, y2 = ring[i - 1]
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    hit = not hit
        return hit

    def at(self, lon: float, lat: float) -> dict | None:
        """The municipality containing this point, or None if it is outside the state."""
        for xmin, ymin, xmax, ymax, rings, props in self.prepared:
            if xmin <= lon <= xmax and ymin <= lat <= ymax and self._inside(rings, lon, lat):
                return props
        return None
