# -*- coding: utf-8 -*-
"""Tests de la logique pure : pytest test/"""
import pytest

from qgis_plugin_graphique import core

ROWS = [
    {"DATE": 2021, "EPCI": "A", "S": 1.5},
    {"DATE": 2021, "EPCI": "B", "S": 2.0},
    {"DATE": 2022, "EPCI": "A", "S": 3.0},
    {"DATE": 2023, "EPCI": "A", "S": 4.0},
    {"DATE": 2023, "EPCI": "B", "S": None},
    {"DATE": None, "EPCI": "B", "S": 9.0},
]


def points(series):
    return dict(series.points)


# ---------------------------------------------------------------- valeurs
class Q:
    def __init__(self, null=False):
        self.null = null

    def isNull(self):  # noqa: N802
        return self.null


class QDateLike:
    def toPyDate(self):  # noqa: N802
        import datetime
        return datetime.date(2024, 5, 17)


def test_normalize_value():
    assert core.normalize_value(None) is None
    assert core.normalize_value(Q(True)) is None
    assert core.normalize_value(float("nan")) is None
    assert core.normalize_value(QDateLike()) == "2024-05-17"
    assert core.normalize_value(5) == 5


@pytest.mark.parametrize("raw, expected", [
    (3, 3.0), ("12,5", 12.5), (" 1 000 ", 1000.0), ("abc", None), ("", None),
    (None, None), (True, None), (float("inf"), None),
])
def test_to_number(raw, expected):
    assert core.to_number(raw) == expected


def test_parse_optional_float():
    assert core.parse_optional_float("") is None
    assert core.parse_optional_float(" 2,5 ") == 2.5
    with pytest.raises(core.ChartError):
        core.parse_optional_float("x")


def test_format_number_and_color():
    assert core.format_number(5.0) == "5" and core.format_number(2.345) == "2.35"
    assert core.format_number(None) == ""
    assert core.valid_color("#AABBCC") == "#AABBCC"
    assert core.valid_color("red; background:url(x)") == core.DEFAULT_COLOR


# ---------------------------------------------------------------- agrégation
def test_sum_by_x_sorted_numeric():
    data = core.build_chart_data(ROWS, ["DATE"], "S", "sum", "x_asc", "bar")
    assert data.numeric_x and data.categories == [2021.0, 2022.0, 2023.0]
    assert data.labels == ["2021", "2022", "2023"]
    assert points(data.series[0]) == {2021.0: 3.5, 2022.0: 3.0, 2023.0: 4.0}


def test_count_without_y_field():
    data = core.build_chart_data(ROWS, ["DATE"], "", "sum", "x_asc", "bar")
    assert points(data.series[0]) == {2021.0: 2.0, 2022.0: 1.0, 2023.0: 2.0}


@pytest.mark.parametrize("how, expected", [
    ("mean", 1.75), ("median", 1.75), ("min", 1.5), ("max", 2.0), ("count", 2.0)])
def test_other_calculations(how, expected):
    data = core.build_chart_data(ROWS, ["DATE"], "S", how, "x_asc", "bar")
    assert points(data.series[0])[2021.0] == expected


def test_no_aggregation_keeps_each_row():
    data = core.build_chart_data(ROWS, ["DATE"], "S", "none", "none", "scatter")
    assert len(data.series[0].points) == 4  # lignes sans S ou sans DATE écartées


def test_x_range_filters_numeric_axis():
    data = core.build_chart_data(ROWS, ["DATE"], "S", "sum", "x_asc", "bar", xmin=2022, xmax=2022)
    assert data.categories == [2022.0]
    with pytest.raises(core.ChartError):
        core.build_chart_data(ROWS, ["DATE"], "S", "sum", "x_asc", "bar", xmin=2030)


def test_multiple_x_fields_make_series():
    data = core.build_chart_data(ROWS, ["DATE", "EPCI"], "S", "sum", "x_asc", "stacked")
    assert [s.name for s in data.series] == ["A", "B"]
    assert points(data.series[0]) == {2021.0: 1.5, 2022.0: 3.0, 2023.0: 4.0}
    assert points(data.series[1]) == {2021.0: 2.0}


def test_text_axis_sorting_and_empty_label():
    rows = [{"k": "b", "v": 1}, {"k": "a", "v": 5}, {"k": None, "v": 2}, {"k": "B", "v": 1}]
    asc = core.build_chart_data(rows, ["k"], "v", "sum", "x_asc", "bar")
    assert not asc.numeric_x and asc.categories == ["(vide)", "a", "b", "B"]
    desc = core.build_chart_data(rows, ["k"], "v", "sum", "y_desc", "bar")
    assert desc.categories[0] == "a"
    first = core.build_chart_data(rows, ["k"], "v", "sum", "none", "bar")
    assert first.categories == ["b", "a", "(vide)", "B"]
    rev = core.build_chart_data(rows, ["k"], "v", "sum", "x_desc", "bar")
    assert rev.categories[0] == "B" or rev.categories[0] == "b"


def test_histogram_needs_y():
    data = core.build_chart_data(ROWS, [], "S", "sum", "x_asc", "hist")
    assert sorted(data.values) == [1.5, 2.0, 3.0, 4.0, 9.0]
    with pytest.raises(core.ChartError):
        core.build_chart_data(ROWS, ["DATE"], "", "sum", "x_asc", "hist")


def test_errors():
    with pytest.raises(core.ChartError):
        core.build_chart_data(ROWS, [], "S", "sum", "x_asc", "bar")
    with pytest.raises(core.ChartError):
        core.build_chart_data(ROWS, ["DATE"], "S", "sum", "x_asc", "radar")
    with pytest.raises(core.ChartError):
        core.build_chart_data([], ["DATE"], "S", "sum", "x_asc", "bar")
    with pytest.raises(core.ChartError):
        core.build_chart_data(ROWS, ["DATE"], "S", "bogus", "x_asc", "bar")


# ---------------------------------------------------------------- lots
def test_split_by_value_with_global_and_ignore():
    groups = core.split_by_value(ROWS, "EPCI", True, "DEPARTEMENT", ["B"])
    assert [g[0] for g in groups] == ["A", "DEPARTEMENT"]
    assert len(groups[0][1]) == 3 and len(groups[1][1]) == len(ROWS)  # le global garde tout


def test_split_by_value_variants():
    assert core.split_by_value(ROWS, "", True) == [("", ROWS)]
    only = core.split_by_value(ROWS, "EPCI", False)
    assert [g[0] for g in only] == ["A", "B"]
    empty = core.split_by_value([{"e": None}], "e", False)
    assert empty[0][0] == "(vide)"


# ---------------------------------------------------------------- noms de fichiers
def test_build_filename_reproduces_original_script():
    values = {"y": "NB", "duree": "5", "valeur": "200012345"}
    assert core.build_filename("{y}_{duree}Ans_{valeur}", values, "png") == "NB_5Ans_200012345.png"


def test_build_filename_is_safe():
    name = core.build_filename("../{valeur}/..\\x", {"valeur": "a/b:c*d"}, "png")
    assert "/" not in name and "\\" not in name and not name.startswith(".")
    assert core.build_filename("", {}, "png") == "graphique.png"
    assert core.build_filename("{valeur}", {"valeur": ""}, "jpg") == "graphique.jpg"
    assert core.build_filename("rapport.png", {}, "png") == "rapport.png"
    assert core.build_filename("a__b_{valeur}_", {"valeur": ""}, "svg") == "a_b.svg"
    assert len(core.build_filename("x" * 500, {}, "png")) <= core.MAX_NAME_LENGTH + 4


def test_unknown_placeholders():
    assert core.unknown_placeholders("{y}_{bidon}_{x}_{autre}") == ["autre", "bidon"]
    assert core.unknown_placeholders("") == []
    for tag in core.PLACEHOLDERS:
        assert core.unknown_placeholders("{" + tag + "}") == []


def test_unique_names():
    assert core.unique_names(["a.png", "A.png", "a.png", "b.png"]) == [
        "a.png", "A_2.png", "a_3.png", "b.png"]


def test_duration():
    assert core.duration(2021, 2025) == "5"
    assert core.duration(2016, 2025) == "10"
    assert core.duration(None, 2025) == "" and core.duration(2.5, 3) == "" and core.duration(5, 1) == ""
