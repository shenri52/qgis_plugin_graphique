# -*- coding: utf-8 -*-
"""Lecture des entités et rattachement spatial à une couche polygonale."""
from qgis.core import (NULL, QgsCoordinateTransform, QgsExpression, QgsFeatureRequest,
                       QgsProject, QgsSpatialIndex)

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
    """Associe les entités selon leur dimension géométrique.

    Polygones : plus grande surface d'intersection.
    Lignes : plus grande longueur d'intersection.
    Points : point représentatif, avec départage par le plus petit FID.
    En cas d'égalité de mesure, le plus petit FID est retenu.
    """
    if polygon_layer is None or polygon_layer.geometryType() != 2:
        raise core.ChartError("La couche de rattachement doit être une couche polygonale.")
    if label_field not in field_names(polygon_layer):
        raise core.ChartError("Le champ de libellé du polygone n'existe plus.")
    error = check_expression(expression)
    if error:
        raise core.ChartError(error)

    source_geometry_type = source_layer.geometryType()
    transform = None
    if source_layer.crs() != polygon_layer.crs():
        if not source_layer.crs().isValid() or not polygon_layer.crs().isValid():
            raise core.ChartError("Les deux couches doivent avoir un SCR défini pour être reprojetées.")
        try:
            transform = QgsCoordinateTransform(
                source_layer.crs(), polygon_layer.crs(), QgsProject.instance())
        except Exception as error:
            raise core.ChartError("Impossible de créer la transformation de SCR : %s" % error)

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
            try:
                if source_geometry_type in (1, 2):
                    # Les mesures sont calculées dans le SCR de la couche polygonale.
                    source_geom = geom
                    if transform is not None:
                        result = source_geom.transform(transform)
                        if result != 0:
                            raise ValueError("échec de la transformation de SCR")
                    candidate_ids = sorted(index.intersects(source_geom.boundingBox()))
                    best_measure = 0.0
                    best_fid = None
                    reason = ("Aucune intersection surfacique avec un polygone"
                              if source_geometry_type == 2
                              else "Aucune intersection linéaire avec un polygone")
                    for fid in candidate_ids:
                        polygon = polygon_features.get(fid)
                        if polygon is None:
                            continue
                        intersection = source_geom.intersection(polygon[0])
                        if intersection is None or intersection.isEmpty():
                            continue
                        measure = (intersection.area() if source_geometry_type == 2
                                   else intersection.length())
                        # Une touche de frontière (mesure nulle) ne crée pas de rattachement.
                        if measure > best_measure or (
                                measure > 0 and measure == best_measure and
                                (best_fid is None or fid < best_fid)):
                            best_measure = measure
                            best_fid = fid
                            match_value = polygon[1]
                    matched = best_fid is not None
                else:
                    # Conserver la méthode actuelle pour les couches ponctuelles.
                    representative = geom.pointOnSurface()
                    if representative is None or representative.isEmpty():
                        representative = geom.centroid()
                    if transform is not None:
                        result = representative.transform(transform)
                        if result != 0:
                            raise ValueError("échec de la transformation de SCR")
                    candidate_ids = sorted(index.intersects(representative.boundingBox()))
                    reason = "Aucun polygone ne contient le point représentatif"
                    for fid in candidate_ids:
                        polygon = polygon_features.get(fid)
                        if polygon and polygon[0].intersects(representative):
                            match_value = polygon[1]
                            matched = True
                            break
            except Exception:
                match_value = None
                matched = False
                reason = "Erreur de géométrie ou de reprojection"
        row["__fid__"] = feature.id()
        if not matched:
            row["__motif__"] = reason
            outside.append(row)
        else:
            row["__territoire__"] = core.EMPTY_LABEL if match_value is None else str(match_value)
            assigned.append(row)
    return assigned, outside
