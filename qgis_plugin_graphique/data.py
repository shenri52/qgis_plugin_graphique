# -*- coding: utf-8 -*-
"""Lecture des entités et rattachement spatial à une couche polygonale."""
from qgis.core import NULL, QgsExpression, QgsFeatureRequest, QgsSpatialIndex

from . import core


def _no_geometry_flag():
    flag = getattr(QgsFeatureRequest, "NoGeometry", None)
    if flag is None:
        flag = QgsFeatureRequest.Flag.NoGeometry
    return flag


def check_expression(text):
    text = (text or "").strip()
    if not text:
        return ""
    expression = QgsExpression(text)
    return expression.parserErrorString() if expression.hasParserError() else ""


def field_names(layer):
    return [field.name() for field in layer.fields()]


def _value(feature, name):
    value = feature[name]
    return None if value == NULL else core.normalize_value(value)


def read_rows(layer, fields, selected_only=False, expression="", cancelled=None):
    """Retourne des dictionnaires attributaires sans charger les géométries."""
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
        rows.append({name: _value(feature, name) for name in wanted})
    return rows


def read_rows_by_polygon(source_layer, polygon_layer, label_field, fields,
                         selected_only=False, expression="", cancelled=None):
    """Associe chaque entité source à un polygone via un point représentatif.

    Pour les géométries surfaciques, pointOnSurface garantit un point intérieur.
    Les entités dont le point ne rencontre aucun polygone sont retournées à part.
    En cas de recouvrement, le polygone de plus petit identifiant QGIS est retenu :
    l'affectation est ainsi déterministe et une entité n'est jamais comptée deux fois.
    """
    if polygon_layer is None or polygon_layer.geometryType() != 2:
        raise core.ChartError("La couche de rattachement doit être une couche polygonale.")
    if label_field not in field_names(polygon_layer):
        raise core.ChartError("Le champ de libellé du polygone n'existe plus.")

    error = check_expression(expression)
    if error:
        raise core.ChartError(error)

    polygon_features = {}
    index = QgsSpatialIndex()
    for polygon in polygon_layer.getFeatures():
        geom = polygon.geometry()
        if geom is None or geom.isEmpty():
            continue
        polygon_features[polygon.id()] = (geom, _value(polygon, label_field))
        index.addFeature(polygon)

    request = QgsFeatureRequest()
    if (expression or "").strip():
        request.setFilterExpression(expression.strip())
    iterator = source_layer.getSelectedFeatures(request) if selected_only else source_layer.getFeatures(request)
    wanted = [name for name in dict.fromkeys(fields) if name]
    assigned, outside = [], []
    for row_number, feature in enumerate(iterator):
        if cancelled is not None and row_number % 250 == 0 and cancelled():
            raise core.ChartError("annulé")
        row = {name: _value(feature, name) for name in wanted}
        geom = feature.geometry()
        match_value = None
        matched = False
        reason = "Géométrie absente"
        if geom is not None and not geom.isEmpty():
            reason = "Aucun polygone ne contient le point représentatif"
            try:
                representative = geom.pointOnSurface()
                if representative is None or representative.isEmpty():
                    representative = geom.centroid()
                candidate_ids = sorted(index.intersects(representative.boundingBox()))
                for fid in candidate_ids:
                    polygon = polygon_features.get(fid)
                    if polygon and polygon[0].intersects(representative):
                        match_value = polygon[1]
                        matched = True
                        break
            except Exception:
                match_value = None
        row["__fid__"] = feature.id()
        if not matched:
            row["__motif__"] = reason
            outside.append(row)
        else:
            row["__territoire__"] = core.EMPTY_LABEL if match_value is None else str(match_value)
            assigned.append(row)
    return assigned, outside
