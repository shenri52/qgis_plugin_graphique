# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("matplotlib")

from qgis_plugin_graphique import core, render  # noqa: E402

ROWS = [{"Y": 2021 + i % 5, "E": "AB"[i % 2], "S": float(i + 1)} for i in range(20)]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def chart(kind, x=("Y",)):
    return core.build_chart_data(ROWS, list(x), "S", "sum", "x_asc", kind)


@pytest.mark.parametrize("kind", core.CHART_TYPES)
def test_every_chart_type_renders(kind):
    x = ("Y", "E") if kind == "stacked" else ("Y",)
    data = chart(kind, x) if kind != "hist" else core.build_chart_data(ROWS, [], "S", "sum", "x_asc", "hist")
    spec = core.ChartSpec(chart_type=kind, title="T", xlabel="x", ylabel="y", show_values=True,
                          grid=True, rotation=30, xmin=2021, xmax=2025, ymin=0, ymax=500)
    assert render.render_png_bytes(data, spec).startswith(PNG_MAGIC)


@pytest.mark.parametrize("fmt, magic", [
    ("png", PNG_MAGIC), ("jpg", b"\xff\xd8"), ("pdf", b"%PDF"), ("tiff", None), ("svg", None)])
def test_save_formats(tmp_path, fmt, magic):
    target = tmp_path / f"out.{fmt}"
    render.save_chart(chart("bar"), core.ChartSpec(dpi=80), str(target), fmt)
    content = target.read_bytes()
    assert content and (magic is None or content.startswith(magic))


def test_unknown_format_rejected(tmp_path):
    with pytest.raises(core.ChartError):
        render.save_chart(chart("bar"), core.ChartSpec(), str(tmp_path / "x.bmp"), "bmp")


def test_size_and_dpi_are_applied(tmp_path):
    from PIL import Image
    target = tmp_path / "a.png"
    render.save_chart(chart("bar"), core.ChartSpec(width=4, height=3, dpi=100), str(target), "png")
    width, height = Image.open(target).size
    assert 300 <= width <= 400 and 220 <= height <= 300  # bbox serrée : un peu moins que 4x3 pouces


def test_pie_without_positive_values():
    rows = [{"k": "a", "v": -1}, {"k": "b", "v": 0}]
    data = core.build_chart_data(rows, ["k"], "v", "sum", "x_asc", "pie")
    with pytest.raises(core.ChartError):
        render.render_png_bytes(data, core.ChartSpec(chart_type="pie"))


def test_axis_limits_applied():
    data = chart("bar")
    spec = core.ChartSpec(xmin=2019, xmax=2027, ymin=-5, ymax=999)
    figure = render.make_figure(data, spec, 50)
    ax = figure.axes[0]
    assert ax.get_ylim() == (-5, 999)
    low, high = ax.get_xlim()
    assert low < 2019 and high > 2027
    assert [t.get_text() for t in ax.get_xticklabels()][0] == "2019"


def test_all_xticks_for_year_range():
    figure = render.make_figure(chart("bar"), core.ChartSpec(xmin=2021, xmax=2025), 50)
    assert [t.get_text() for t in figure.axes[0].get_xticklabels()] == [str(y) for y in range(2021, 2026)]


def test_horizontal_bars_swap_labels():
    figure = render.make_figure(chart("barh"), core.ChartSpec(xlabel="cat", ylabel="val"), 50)
    ax = figure.axes[0]
    assert ax.get_ylabel() == "cat" and ax.get_xlabel() == "val"
