# -*- coding: utf-8 -*-
"""Graphique Couche – plugin QGIS autonome (Qt5 / Qt6)."""


def classFactory(iface):  # noqa: N802
    from .plugin import GraphiquePlugin
    return GraphiquePlugin(iface)
