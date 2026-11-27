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
        x1, y1, x2, y2 = self.bounds
        ox1, oy1, ox2, oy2 = other.bounds
        return not (x2 < ox1 or ox2 < x1 or y2 < oy1 or oy2 < y1)

    def intersection(self, other):
        x1 = max(self.bounds[0], other.bounds[0])
        y1 = max(self.bounds[1], other.bounds[1])
        x2 = min(self.bounds[2], other.bounds[2])
        y2 = min(self.bounds[3], other.bounds[3])
        if x2 < x1 or y2 < y1:
            return FakeMeasure(0, 0)
        if self.bounds[1] == self.bounds[3]:  # ligne horizontale
            return FakeMeasure(0, max(0, x2 - x1))
        if self.bounds[0] == self.bounds[2]:  # ligne verticale
            return FakeMeasure(0, max(0, y2 - y1))
        return FakeMeasure(max(0, (x2 - x1) * (y2 - y1)), 0)


class FakeMeasure:
    def __init__(self, area, length):
        self._area, self._length = area, length

    def isEmpty(self):
        return self._area == 0 and self._length == 0

    def area(self):
        return self._area

    def length(self):
        return self._length


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



def test_polygon_source_uses_largest_intersection_area():
    polygons = FakeLayer([
        qgis_stubs.FakeFeature({"CODE": "A"}, FakeGeometry((0, 0, 5, 10)), 1),
        qgis_stubs.FakeFeature({"CODE": "B"}, FakeGeometry((4, 0, 10, 10)), 2),
    ], ["CODE"], geometry_type=2)
    source = FakeLayer([
        qgis_stubs.FakeFeature({"VALUE": 8}, FakeGeometry((2, 1, 8, 9)), 99),
    ], ["VALUE"], geometry_type=2)

    assigned, outside = data.read_rows_by_polygon(source, polygons, "CODE", ["VALUE"])

    assert not outside
    assert assigned[0]["__territoire__"] == "B"


def test_polygon_boundary_touch_matches_intersects_predicate():
    polygons = FakeLayer([
        qgis_stubs.FakeFeature({"CODE": "A"}, FakeGeometry((0, 0, 5, 10)), 10),
        qgis_stubs.FakeFeature({"CODE": "B"}, FakeGeometry((5, 0, 10, 10)), 20),
    ], ["CODE"], geometry_type=2)
    # Le polygone source touche A par une frontière seulement : aire d'intersection nulle.
    source = FakeLayer([
        qgis_stubs.FakeFeature({"VALUE": 8}, FakeGeometry((5, 2, 8, 8)), 99),
    ], ["VALUE"], geometry_type=2)

    assigned, outside = data.read_rows_by_polygon(source, polygons, "CODE", ["VALUE"])

    assert not outside
    assert assigned[0]["__territoire__"] == "B"

    # Contact uniquement sur la frontière commune : intersects vrai, mesure nulle,
    # départage déterministe par le plus petit FID.
    source = FakeLayer([
        qgis_stubs.FakeFeature({"VALUE": 8}, FakeGeometry((5, 2, 5, 8)), 100),
    ], ["VALUE"], geometry_type=2)
    assigned, outside = data.read_rows_by_polygon(source, polygons, "CODE", ["VALUE"])
    assert not outside
    assert assigned[0]["__territoire__"] == "A"


def test_line_source_uses_largest_intersection_length_and_fid_tie_break():
    polygons = FakeLayer([
        qgis_stubs.FakeFeature({"CODE": "A"}, FakeGeometry((0, 0, 4, 10)), 10),
        qgis_stubs.FakeFeature({"CODE": "B"}, FakeGeometry((3, 0, 10, 10)), 20),
    ], ["CODE"], geometry_type=2)
    source = FakeLayer([
        qgis_stubs.FakeFeature({"VALUE": 8}, FakeGeometry((0, 5, 10, 5)), 99),
    ], ["VALUE"], geometry_type=1)

    assigned, outside = data.read_rows_by_polygon(source, polygons, "CODE", ["VALUE"])

    assert not outside
    assert assigned[0]["__territoire__"] == "B"

    # Deux intersections de même longueur : le plus petit FID gagne.
    tied_polygons = FakeLayer([
        qgis_stubs.FakeFeature({"CODE": "B"}, FakeGeometry((3, 0, 10, 10)), 20),
        qgis_stubs.FakeFeature({"CODE": "A"}, FakeGeometry((0, 0, 7, 10)), 10),
    ], ["CODE"], geometry_type=2)
    assigned, outside = data.read_rows_by_polygon(source, tied_polygons, "CODE", ["VALUE"])
    assert not outside
    assert assigned[0]["__territoire__"] == "A"
