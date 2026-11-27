# -*- coding: utf-8 -*-
"""Faux module `qgis` (sans QGIS) pour tester le plugin avec PyQt5 ou PyQt6."""
import importlib
import re
import sys
import types


class FakeNull:
    """Équivalent de qgis.core.NULL."""

    def isNull(self):  # noqa: N802
        return True

    def __eq__(self, other):
        return isinstance(other, FakeNull)

    def __hash__(self):
        return 0


NULL = FakeNull()


class FakeSettings:
    store = {}

    def value(self, key, default=None, type=None):  # noqa: A002
        return self.store.get(key, default)

    def setValue(self, key, value):  # noqa: N802
        self.store[key] = value


class FakeApplication:
    @staticmethod
    def locale():
        return "fr"


class FakeField:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class FakeFeature:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, key):
        return self._values[key]


class FakeRequest:
    NoGeometry = 1

    def __init__(self):
        self.expression = ""
        self.flags = 0

    def setFlags(self, flags):  # noqa: N802
        self.flags = flags

    def setFilterExpression(self, text):  # noqa: N802
        self.expression = text


class FakeSpatialIndex:
    def __init__(self, *_args, **_kwargs):
        self.features = []

    def addFeature(self, feature):  # noqa: N802
        self.features.append(feature)

    def intersects(self, _rectangle):
        return []


class FakeExpression:
    def __init__(self, text):
        self.text = text

    def hasParserError(self):  # noqa: N802
        return self.text.count("(") != self.text.count(")") or self.text.endswith(">=")

    def parserErrorString(self):  # noqa: N802
        return "syntax error"


class QgsVectorLayer:
    """Faux couche vectorielle."""
    _counter = 0

    def __init__(self, name, field_names, records, selected=()):
        QgsVectorLayer._counter += 1
        self._name, self._id = name, f"layer_{QgsVectorLayer._counter}"
        self._fields = [FakeField(n) for n in field_names]
        self._records = records
        self._selected = set(selected)

    def name(self):
        return self._name

    def id(self):
        return self._id

    def fields(self):
        return self._fields

    @staticmethod
    def _matches(record, expression):
        if not expression:
            return True
        found = re.match(r'^"(\w+)"\s*(>=|<=|=|>|<)\s*(-?\d+(?:\.\d+)?)$', expression)
        if not found:
            return True
        field, operator, number = found.group(1), found.group(2), float(found.group(3))
        value = record[field]
        if isinstance(value, FakeNull) or value is None:
            return False
        return {">=": value >= number, "<=": value <= number, "=": value == number,
                ">": value > number, "<": value < number}[operator]

    def getFeatures(self, request=None):  # noqa: N802
        expression = request.expression if request else ""
        return iter([FakeFeature(r) for r in self._records if self._matches(r, expression)])

    def getSelectedFeatures(self, request=None):  # noqa: N802
        expression = request.expression if request else ""
        return iter([FakeFeature(r) for i, r in enumerate(self._records)
                     if i in self._selected and self._matches(r, expression)])


class FakeProject:
    _instance = None

    def __init__(self):
        self.layers = {}

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def mapLayers(self):  # noqa: N802
        return dict(self.layers)

    def mapLayer(self, layer_id):  # noqa: N802
        return self.layers.get(layer_id)


def install(qt="PyQt6"):
    mods = {name: importlib.import_module(f"{qt}.{name}")
            for name in ("QtCore", "QtGui", "QtWidgets")}
    if not hasattr(mods["QtGui"], "QAction"):  # PyQt5 : l'équivalent de la couche qgis.PyQt
        mods["QtGui"].QAction = mods["QtWidgets"].QAction
    for name in ("qgis", "qgis.PyQt"):
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    for name, module in mods.items():
        sys.modules[f"qgis.PyQt.{name}"] = module
    core = types.ModuleType("qgis.core")
    core.QgsApplication = FakeApplication
    core.QgsSettings = FakeSettings
    core.QgsProject = FakeProject
    core.QgsVectorLayer = QgsVectorLayer
    core.QgsFeatureRequest = FakeRequest
    core.QgsSpatialIndex = FakeSpatialIndex
    core.QgsExpression = FakeExpression
    core.NULL = NULL
    sys.modules["qgis.core"] = core
    gui = types.ModuleType("qgis.gui")

    class FakeExpressionBuilderDialog:
        def __init__(self, layer, expression="", parent=None):
            self._expression = expression

        def exec(self):
            return 0

        def expressionText(self):
            return self._expression

    gui.QgsExpressionBuilderDialog = FakeExpressionBuilderDialog
    sys.modules["qgis.gui"] = gui
    return mods
