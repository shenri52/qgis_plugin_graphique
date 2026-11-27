# -*- coding: utf-8 -*-
"""Tests du rattachement spatial avec géométries minimales simulées."""
import qgis_stubs
qgis_stubs.install("PyQt6")

from qgis_plugin_graphique import core, data


class FakeGeometry:
    def __init__(self, bounds, point=False):
        self.bounds = bounds
        self.point = point

    def isEmpty(self):
        return False

    def pointOnSurface(self):
        if self.point:
            return self
        x1, y1, x2, y2 = self.bounds
        return FakeGeometry(((x1 + x2) / 2, (y1 + y2) / 2,
                             (x1 + x2) / 2, (y1 + y2) / 2), point=True)

    def centroid(self):
        return self.pointOnSurface()

    def boundingBox(self):
        return self.bounds

    def intersects(self, other):
        x, y, _x2, _y2 = other.bounds
        x1, y1, x2, y2 = self.bounds
        return x1 <= x <= x2 and y1 <= y <= y2


class FakeLayer:
    def __init__(self, records, fields, geometry_type=0):
        self.records = records
        self._fields = [qgis_stubs.FakeField(name) for name in fields]
        self._geometry_type = geometry_type

    def geometryType(self):
        return self._geometry_type

    def fields(self):
        return self._fields

    def crs(self):
        return "EPSG:2154"

    def getFeatures(self, _request=None):
        return iter(self.records)

    def getSelectedFeatures(self, _request=None):
        return iter(self.records)


def test_spatial_assignment_excludes_unmatched_and_is_deterministic():
    polygons = FakeLayer([
        qgis_stubs.FakeFeature({"CODE": "A"}, FakeGeometry((0, 0, 10, 10)), 10),
        qgis_stubs.FakeFeature({"CODE": "B"}, FakeGeometry((0, 0, 10, 10)), 20),
        qgis_stubs.FakeFeature({"CODE": None}, FakeGeometry((12, 12, 18, 18)), 30),
    ], ["CODE"], geometry_type=2)
    source = FakeLayer([
        qgis_stubs.FakeFeature({"DATE": 2024, "VALUE": 5},
                               FakeGeometry((4, 4, 4, 4), point=True), 101),
        qgis_stubs.FakeFeature({"DATE": 2024, "VALUE": 7},
                               FakeGeometry((15, 15, 15, 15), point=True), 102),
        qgis_stubs.FakeFeature({"DATE": 2024, "VALUE": 9},
                               FakeGeometry((30, 30, 30, 30), point=True), 103),
    ], ["DATE", "VALUE"])
    assigned, outside = data.read_rows_by_polygon(
        source, polygons, "CODE", ["DATE", "VALUE"])

    assert [row["__territoire__"] for row in assigned] == ["A", core.EMPTY_LABEL]
    assert [row["__fid__"] for row in outside] == [103]
    assert outside[0]["__motif__"] == "Aucun polygone ne contient le point représentatif"
    # L'entité dans deux polygones n'est comptée qu'une fois, dans le premier FID.
    assert len(assigned) == 2
