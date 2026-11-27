# -*- coding: utf-8 -*-
"""Logique pure (sans QGIS ni matplotlib) : agrégation, filtres, noms de fichiers.

Tout ce module est testable avec pytest, sans QGIS.
"""
import math
import re
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime

CHART_TYPES = ("bar", "barh", "stacked", "line", "area", "scatter", "pie", "hist")
AGGREGATIONS = ("sum", "mean", "median", "min", "max", "count", "none")
SORTS = ("x_asc", "x_desc", "none", "y_desc")
IMAGE_FORMATS = ("png", "jpg", "svg", "pdf", "tiff")
PLACEHOLDERS = ("couche", "x", "y", "type", "agregation", "valeur", "xmin", "xmax", "duree", "date", "aamm")
EMPTY_LABEL = "(vide)"
DEFAULT_COLOR = "#8fc7e8"
MAX_NAME_LENGTH = 150

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class ChartError(ValueError):
    """Erreur affichable à l'utilisateur (données ou réglages invalides)."""


# ------------------------------------------------------------------ valeurs
def normalize_value(value):
    """Convertit une valeur de couche (NULL, QDate, QDateTime...) en type Python simple."""
    if value is None:
        return None
    is_null = getattr(value, "isNull", None)
    if callable(is_null):
        try:
            if is_null():
                return None
        except TypeError:
            return value
    for method in ("toPyDateTime", "toPyDate"):
        converter = getattr(value, method, None)
        if callable(converter):
            return converter().isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def to_number(value):
    """Retourne un float, ou None si la valeur n'est pas numérique."""
    value = normalize_value(value)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    return number if math.isfinite(number) else None


def parse_optional_float(text):
    """'' -> None ; '12,5' -> 12.5 ; texte invalide -> ChartError."""
    text = (text or "").strip()
    if not text:
        return None
    number = to_number(text)
    if number is None:
        raise ChartError(text)
    return number


def format_number(value):
    """12.0 -> '12' ; 12.345 -> '12.35'."""
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def valid_color(color):
    return color if isinstance(color, str) and _HEX_COLOR.match(color) else DEFAULT_COLOR


# ------------------------------------------------------------------ données du graphique
@dataclass
class Series:
    name: str
    points: list = field(default_factory=list)  # [(clé x, valeur y)]


@dataclass
class ChartData:
    kind: str = "bar"
    numeric_x: bool = False
    categories: list = field(default_factory=list)  # clés x triées, uniques
    labels: list = field(default_factory=list)       # libellés texte des catégories
    series: list = field(default_factory=list)
    values: list = field(default_factory=list)       # histogramme : valeurs brutes


def _aggregate(values, how):
    if how == "sum":
        return math.fsum(values)
    if how == "mean":
        return math.fsum(values) / len(values)
    if how == "median":
        return statistics.median(values)
    if how == "min":
        return min(values)
    return max(values)


def _label(key, numeric):
    if numeric:
        return format_number(key)
    return str(key)


def build_chart_data(rows, x_fields, y_field, how, sort, chart_type, y_name="",
                     xmin=None, xmax=None):
    """Construit les séries à tracer.

    - x_fields[0] est l'axe ; les champs suivants définissent les séries (valeurs combinées).
    - y_field vide : comptage des entités.
    - how = 'none' : une valeur par entité, sans regroupement.
    """
    if chart_type not in CHART_TYPES:
        raise ChartError(f"type: {chart_type}")
    if how not in AGGREGATIONS or sort not in SORTS:
        raise ChartError("agrégation ou tri inconnu")

    if chart_type == "hist":
        if not y_field:
            raise ChartError("histogramme : choisissez un champ Y numérique")
        values = [n for n in (to_number(r.get(y_field)) for r in rows) if n is not None]
        if not values:
            raise ChartError("aucune valeur numérique")
        return ChartData(kind="hist", values=values)

    if not x_fields:
        raise ChartError("aucun champ X")
    axis, series_fields = x_fields[0], list(x_fields[1:])
    if not y_field:
        how = "count"

    axis_values = [normalize_value(r.get(axis)) for r in rows]
    present = [v for v in axis_values if v is not None]
    numeric_x = bool(present) and all(to_number(v) is not None for v in present)

    series_order, grouped, key_order = [], {}, []
    for row, raw_x in zip(rows, axis_values):
        if numeric_x:
            if raw_x is None:
                continue
            key = to_number(raw_x)
            if (xmin is not None and key < xmin) or (xmax is not None and key > xmax):
                continue
        else:
            key = EMPTY_LABEL if raw_x is None else str(raw_x)
        if series_fields:
            name = " / ".join(
                EMPTY_LABEL if normalize_value(row.get(f)) is None else str(normalize_value(row.get(f)))
                for f in series_fields)
        else:
            name = y_name or y_field or "n"
        y_number = to_number(row.get(y_field)) if y_field else None
        if how != "count" and y_number is None:
            continue
        if name not in grouped:
            grouped[name] = {}
            series_order.append(name)
        if key not in key_order:
            key_order.append(key)
        grouped[name].setdefault(key, []).append(1.0 if how == "count" else y_number)

    if not grouped:
        raise ChartError("aucune donnée à tracer")

    series = []
    for name in series_order:
        points = []
        for key, values in grouped[name].items():
            if how == "none":
                points.extend((key, v) for v in values)
            elif how == "count":
                points.append((key, float(len(values))))
            else:
                points.append((key, _aggregate(values, how)))
        series.append(Series(name, points))

    totals = {k: 0.0 for k in key_order}
    for s in series:
        for key, value in s.points:
            totals[key] += value

    if sort == "x_asc":
        categories = sorted(key_order, key=(lambda k: k) if numeric_x else (lambda k: k.casefold()))
    elif sort == "x_desc":
        categories = sorted(key_order, key=(lambda k: k) if numeric_x else (lambda k: k.casefold()),
                            reverse=True)
    elif sort == "y_desc":
        categories = sorted(key_order, key=lambda k: totals[k], reverse=True)
    else:
        categories = list(key_order)

    return ChartData(kind=chart_type, numeric_x=numeric_x, categories=categories,
                     labels=[_label(k, numeric_x) for k in categories], series=series)


# ------------------------------------------------------------------ lots (un graphique par valeur)
def split_by_value(rows, batch_field, include_global=True, global_label="TOTAL", ignore=()):
    """[(libellé, lignes)] : un jeu par valeur du champ, puis le jeu global (toutes les lignes)."""
    if not batch_field:
        return [("", list(rows))]
    ignored = {str(v).strip() for v in ignore if str(v).strip()}
    groups, order = {}, []
    for row in rows:
        value = normalize_value(row.get(batch_field))
        label = EMPTY_LABEL if value is None else str(value)
        if label not in groups:
            groups[label] = []
            order.append(label)
        groups[label].append(row)
    result = [(label, groups[label]) for label in sorted(order, key=str.casefold)
              if label not in ignored]
    if include_global:
        result.append((global_label or "TOTAL", list(rows)))
    return result


# ------------------------------------------------------------------ noms de fichiers
def sanitize_filename(text):
    """Garde lettres, chiffres, espace, _ - . ; supprime tout séparateur de chemin."""
    cleaned = "".join(c for c in str(text) if c.isalnum() or c in " _-.")
    return cleaned.strip(" .")[:MAX_NAME_LENGTH]


def unknown_placeholders(pattern):
    return sorted({m for m in _PLACEHOLDER.findall(pattern or "") if m not in PLACEHOLDERS})


def build_filename(pattern, values, extension):
    """Remplace {balises} par des valeurs nettoyées ; ajoute l'extension si absente."""
    def replace(match):
        return sanitize_filename(values.get(match.group(1), ""))

    name = _PLACEHOLDER.sub(replace, pattern or "")
    name = re.sub(r"_{2,}", "_", sanitize_filename(name)).strip("_ ")
    if not name:
        name = "graphique"
    suffix = "." + extension.lower()
    if name.lower().endswith(suffix):
        name = name[: -len(suffix)] or "graphique"
    return name + suffix


def unique_names(names):
    """Rend uniques des noms en doublon (a.png, a_2.png, ...)."""
    seen, result = {}, []
    for name in names:
        key = name.lower()
        if key not in seen:
            seen[key] = 1
            result.append(name)
            continue
        seen[key] += 1
        stem, dot, ext = name.rpartition(".")
        candidate = f"{stem}_{seen[key]}{dot}{ext}"
        while candidate.lower() in seen:
            seen[key] += 1
            candidate = f"{stem}_{seen[key]}{dot}{ext}"
        seen[candidate.lower()] = 1
        result.append(candidate)
    return result


def duration(xmin, xmax):
    """Nombre d'entiers dans [xmin, xmax] (ex. 2021..2025 -> 5) ; '' si non applicable."""
    if xmin is None or xmax is None or not (float(xmin).is_integer() and float(xmax).is_integer()):
        return ""
    return str(int(xmax - xmin) + 1) if xmax >= xmin else ""


@dataclass
class ChartSpec:
    """Tous les réglages d'aspect d'un graphique."""
    chart_type: str = "bar"
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    xmin: float = None
    xmax: float = None
    ymin: float = None
    ymax: float = None
    color: str = DEFAULT_COLOR
    width: float = 5.85
    height: float = 4.13
    dpi: int = 200
    legend: bool = True
    grid: bool = False
    show_values: bool = False
    hide_spines: bool = True
    integer_y: bool = True
    all_xticks: bool = True
    rotation: int = 0
    bins: int = 10
