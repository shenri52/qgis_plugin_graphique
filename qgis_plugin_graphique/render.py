# -*- coding: utf-8 -*-
"""Dessin des graphiques avec matplotlib (sans pyplot : aucun état global, aucune fenêtre)."""
import io
import math

from . import core

PALETTE = ("#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2",
           "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac")
MAX_TICKS = 60
PREVIEW_DPI = 100
MATPLOTLIB_FORMATS = {"png": "png", "jpg": "jpg", "svg": "svg", "pdf": "pdf", "tiff": "tiff"}


def matplotlib_available():
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def _new_figure(spec, dpi):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(spec.width, spec.height), dpi=dpi, facecolor="white")
    FigureCanvasAgg(figure)
    return figure


def _colors(spec, count):
    if count <= 1:
        return [core.valid_color(spec.color)]
    return [PALETTE[i % len(PALETTE)] for i in range(count)]


def _positions(data):
    """Position de chaque catégorie sur l'axe (valeur réelle si X numérique, sinon 0..n-1)."""
    if data.numeric_x:
        return {key: float(key) for key in data.categories}
    return {key: float(i) for i, key in enumerate(data.categories)}


def _gap(positions):
    values = sorted(set(positions.values()))
    diffs = [b - a for a, b in zip(values, values[1:]) if b - a > 0]
    return min(diffs) if diffs else 1.0


def _lookup(series, category):
    return sum(v for k, v in series.points if k == category) if series.points else 0.0


def _annotate(ax, x, y, value, horizontal):
    label = core.format_number(value)
    if horizontal:
        ax.annotate(label, (y, x), xytext=(3, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=7)
    else:
        ax.annotate(label, (x, y), xytext=(0, 2), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7)


def _draw_bars(ax, data, spec, horizontal, stacked):
    positions = _positions(data)
    gap = _gap(positions)
    count = len(data.series)
    colors = _colors(spec, count)
    group_width = 0.8 * gap
    bar_width = group_width if stacked or count == 1 else group_width / count
    bottoms = {key: 0.0 for key in data.categories}
    for index, series in enumerate(data.series):
        xs, heights, lefts = [], [], []
        for key in data.categories:
            value = _lookup(series, key)
            offset = 0.0 if stacked or count == 1 else (index - (count - 1) / 2) * bar_width
            xs.append(positions[key] + offset)
            heights.append(value)
            lefts.append(bottoms[key] if stacked else 0.0)
        draw = ax.barh if horizontal else ax.bar
        kwargs = {"left" if horizontal else "bottom": lefts}
        draw(xs, heights, bar_width * (1.0 if horizontal else 1.0), color=colors[index],
             label=series.name, **kwargs)
        if spec.show_values:
            for x, height, base in zip(xs, heights, lefts):
                if height:
                    _annotate(ax, x, base + height, height, horizontal)
        if stacked:
            for key, height in zip(data.categories, heights):
                bottoms[key] += height
    return positions, gap


def _draw_lines(ax, data, spec, area):
    positions = _positions(data)
    colors = _colors(spec, len(data.series))
    for index, series in enumerate(data.series):
        points = sorted(((positions[k], v) for k, v in series.points), key=lambda p: p[0])
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        if area:
            ax.fill_between(xs, ys, alpha=0.45, color=colors[index])
        ax.plot(xs, ys, marker="o", markersize=3, color=colors[index], label=series.name)
        if spec.show_values:
            for x, y in points:
                _annotate(ax, x, y, y, False)
    return positions, _gap(positions)


def _draw_scatter(ax, data, spec):
    positions = _positions(data)
    colors = _colors(spec, len(data.series))
    for index, series in enumerate(data.series):
        xs = [positions[k] for k, _ in series.points]
        ys = [v for _, v in series.points]
        ax.scatter(xs, ys, s=14, color=colors[index], label=series.name)
        if spec.show_values:
            for x, y in zip(xs, ys):
                _annotate(ax, x, y, y, False)
    return positions, _gap(positions)


def _draw_pie(ax, data, spec):
    totals = []
    for key, label in zip(data.categories, data.labels):
        total = sum(_lookup(s, key) for s in data.series)
        if total > 0 and math.isfinite(total):
            totals.append((label, total))
    if not totals:
        raise core.ChartError("camembert : aucune valeur positive")
    labels = [t[0] for t in totals]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(totals))]
    ax.pie([t[1] for t in totals], labels=labels if not spec.legend else None, colors=colors,
           autopct="%1.1f%%" if spec.show_values else None, startangle=90, counterclock=False,
           textprops={"fontsize": 8})
    ax.axis("equal")
    if spec.legend:
        ax.legend(labels, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)


def _apply_axes(ax, data, spec, positions, gap, horizontal):
    category_axis = ax.yaxis if horizontal else ax.xaxis
    set_ticks = ax.set_yticks if horizontal else ax.set_xticks
    set_labels = ax.set_yticklabels if horizontal else ax.set_xticklabels
    set_cat_lim = ax.set_ylim if horizontal else ax.set_xlim
    set_val_lim = ax.set_xlim if horizontal else ax.set_ylim
    bar_like = data.kind in ("bar", "barh", "stacked")

    if data.numeric_x:
        ticks = None
        if (spec.all_xticks and spec.xmin is not None and spec.xmax is not None
                and float(spec.xmin).is_integer() and float(spec.xmax).is_integer()
                and 0 <= spec.xmax - spec.xmin <= MAX_TICKS):
            ticks = [float(v) for v in range(int(spec.xmin), int(spec.xmax) + 1)]
        elif spec.all_xticks and len(data.categories) <= MAX_TICKS:
            ticks = [positions[k] for k in data.categories]
        if ticks:
            set_ticks(ticks)
            set_labels([core.format_number(t) for t in ticks])
    elif data.categories:
        set_ticks([positions[k] for k in data.categories])
        set_labels(data.labels)

    margin = 0.6 * gap if bar_like else 0.0
    if data.numeric_x and (spec.xmin is not None or spec.xmax is not None):
        low, high = category_axis.get_view_interval()
        low = spec.xmin - margin if spec.xmin is not None else low
        high = spec.xmax + margin if spec.xmax is not None else high
        if low < high:
            set_cat_lim(low, high)
    if spec.ymin is not None or spec.ymax is not None:
        value_axis = ax.xaxis if horizontal else ax.yaxis
        low, high = value_axis.get_view_interval()
        low = spec.ymin if spec.ymin is not None else low
        high = spec.ymax if spec.ymax is not None else high
        if low < high:
            set_val_lim(low, high)
    if spec.integer_y:
        from matplotlib import ticker
        (ax.xaxis if horizontal else ax.yaxis).set_major_locator(ticker.MaxNLocator(integer=True))
    if spec.rotation:
        ax.tick_params(axis="y" if horizontal else "x", labelrotation=spec.rotation)
        if not horizontal:
            for label in ax.get_xticklabels():
                label.set_ha("right" if spec.rotation < 90 else "center")


def _draw(figure, data, spec):
    ax = figure.add_subplot(111)
    if data.kind == "pie":
        _draw_pie(ax, data, spec)
        if spec.title:
            ax.set_title(spec.title)
        return
    horizontal = data.kind == "barh"
    if data.kind == "hist":
        ax.hist(data.values, bins=max(1, int(spec.bins)), color=core.valid_color(spec.color),
                edgecolor="white")
        if spec.integer_y:
            from matplotlib import ticker
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        if spec.xmin is not None or spec.xmax is not None:
            low, high = ax.get_xlim()
            ax.set_xlim(spec.xmin if spec.xmin is not None else low,
                        spec.xmax if spec.xmax is not None else high)
        if spec.ymin is not None or spec.ymax is not None:
            low, high = ax.get_ylim()
            ax.set_ylim(spec.ymin if spec.ymin is not None else low,
                        spec.ymax if spec.ymax is not None else high)
        positions, gap = {}, 1.0
    elif data.kind in ("bar", "barh", "stacked"):
        positions, gap = _draw_bars(ax, data, spec, horizontal, data.kind == "stacked")
    elif data.kind in ("line", "area"):
        positions, gap = _draw_lines(ax, data, spec, data.kind == "area")
    else:
        positions, gap = _draw_scatter(ax, data, spec)

    if data.kind != "hist":
        _apply_axes(ax, data, spec, positions, gap, horizontal)
    if spec.title:
        ax.set_title(spec.title)
    xlabel, ylabel = spec.xlabel, spec.ylabel
    if horizontal:
        xlabel, ylabel = ylabel, xlabel
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if spec.grid:
        ax.grid(True, alpha=0.3)
    if spec.hide_spines:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    if spec.legend and data.kind != "hist" and len(data.series) > 1:
        ax.legend(fontsize=8, frameon=False)


def make_figure(data, spec, dpi):
    figure = _new_figure(spec, dpi)
    _draw(figure, data, spec)
    return figure


def render_png_bytes(data, spec):
    """Aperçu : PNG en mémoire, résolution fixe et modérée."""
    figure = make_figure(data, spec, PREVIEW_DPI)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=PREVIEW_DPI, bbox_inches="tight", facecolor="white")
    return buffer.getvalue()


def save_chart(data, spec, path, fmt):
    """Exporte le graphique dans le format demandé (png, jpg, svg, pdf, tiff)."""
    if fmt not in MATPLOTLIB_FORMATS:
        raise core.ChartError(f"format: {fmt}")
    figure = make_figure(data, spec, spec.dpi)
    figure.savefig(path, format=MATPLOTLIB_FORMATS[fmt], dpi=spec.dpi, bbox_inches="tight",
                   facecolor="white")
