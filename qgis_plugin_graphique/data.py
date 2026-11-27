# -*- coding: utf-8 -*-
"""Lecture des entités d'une couche vectorielle QGIS (seul module qui touche à l'API QGIS)."""
from qgis.core import NULL, QgsExpression, QgsFeatureRequest

from . import core


def _no_geometry_flag():
    flag = getattr(QgsFeatureRequest, "NoGeometry", None)
    if flag is None:
        flag = QgsFeatureRequest.Flag.NoGeometry
    return flag


def check_expression(text):
    """Retourne le message d'erreur de l'expression, ou '' si elle est valide."""
    text = (text or "").strip()
    if not text:
        return ""
    expression = QgsExpression(text)
    return expression.parserErrorString() if expression.hasParserError() else ""


def field_names(layer):
    return [field.name() for field in layer.fields()]


def read_rows(layer, fields, selected_only=False, expression="", cancelled=None):
    """Retourne une liste de dictionnaires {champ: valeur simple} pour les champs demandés."""
    error = check_expression(expression)
    if error:
        raise core.ChartError(error)
    request = QgsFeatureRequest()
    request.setFlags(_no_geometry_flag())
    if (expression or "").strip():
        request.setFilterExpression(expression.strip())
    iterator = layer.getSelectedFeatures(request) if selected_only else layer.getFeatures(request)
    wanted = [name for name in dict.fromkeys(fields) if name]
    rows = []
    for index, feature in enumerate(iterator):
        if cancelled is not None and index % 500 == 0 and cancelled():
            raise core.ChartError("annulé")
        row = {}
        for name in wanted:
            value = feature[name]
            row[name] = None if value == NULL else core.normalize_value(value)
        rows.append(row)
    return rows
