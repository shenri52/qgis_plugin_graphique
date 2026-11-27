# -*- coding: utf-8 -*-
"""Fenêtre principale de Graphique Couche : réglages à gauche, aperçu à droite."""
import csv
import os
from datetime import datetime

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox,
    QSplitter, QTabWidget, QVBoxLayout, QWidget, QColorDialog,
)
from qgis.core import QgsProject, QgsSettings, QgsVectorLayer
from qgis.gui import QgsExpressionBuilderDialog

from . import core, data, render
from .i18n import PRESET_NAMES, tr

SETTINGS_PREFIX = "GraphiqueCouche/"
NO_FIELD = ""

CHART_LABELS = (
    ("bar", "Histogramme (barres)"), ("barh", "Barres horizontales"),
    ("stacked", "Barres empilées"), ("line", "Courbe"), ("area", "Aire"),
    ("scatter", "Nuage de points"), ("pie", "Camembert"),
    ("hist", "Histogramme de distribution (champ Y)"),
)
AGG_LABELS = (
    ("sum", "Somme"), ("mean", "Moyenne"), ("median", "Médiane"), ("min", "Minimum"),
    ("max", "Maximum"), ("count", "Comptage"), ("none", "Aucun (une valeur par entité)"),
)
SORT_LABELS = (
    ("x_asc", "X croissant"), ("x_desc", "X décroissant"),
    ("none", "Ordre de la couche"), ("y_desc", "Y décroissant"),
)
FORMAT_LABELS = (("png", "PNG"), ("jpg", "JPEG"), ("svg", "SVG"), ("pdf", "PDF"), ("tiff", "TIFF"))


def _combo(items):
    box = QComboBox()
    for key, label in items:
        box.addItem(tr(label), key)
    return box


class GraphDialog(QDialog):
    """Choix de la couche, des champs, du type de graphique, aperçu et export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Graphique Couche"))
        self.resize(1100, 640)
        self._color = core.DEFAULT_COLOR
        self._series_colors = {}
        self._pixmap = None
        self._running = False
        self._cancel = False
        self._build_ui()
        self.refresh_layers()
        self._load_settings()
        self._update_visibility()
        self._update_filename_preview()

    # ------------------------------------------------------------------ interface
    def _build_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_data_tab(), tr("Données"))
        self.tabs.addTab(self._build_chart_tab(), tr("Graphique"))
        self.tabs.addTab(self._build_export_tab(), tr("Export"))
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._build_preview_pane())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([430, 670])

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.preview_button = QPushButton(tr("Aperçu"))
        self.export_button = QPushButton(tr("Exporter"))
        self.cancel_button = QPushButton(tr("Annuler"))
        self.cancel_button.setVisible(False)
        self.close_button = QPushButton(tr("Fermer"))
        self.preview_button.clicked.connect(self._preview)
        self.export_button.clicked.connect(self._export)
        self.cancel_button.clicked.connect(self._request_cancel)
        self.close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.progress, 1)
        for button in (self.preview_button, self.export_button, self.cancel_button, self.close_button):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

    def _build_data_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        row = QHBoxLayout()
        self.layer_combo = QComboBox()
        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setToolTip(tr("Actualiser la liste des couches"))
        self.refresh_button.setMaximumWidth(32)
        row.addWidget(self.layer_combo, 1)
        row.addWidget(self.refresh_button)
        form = QFormLayout()
        form.addRow(tr("Couche"), row)
        self.selected_only = QCheckBox(tr("Entités sélectionnées uniquement"))
        form.addRow(self.selected_only)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(tr("ex. \"DATE\" >= 2021"))
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_edit, 1)
        self.expression_button = QPushButton(tr("Constructeur…"))
        self.expression_button.clicked.connect(self._open_expression_builder)
        filter_row.addWidget(self.expression_button)
        form.addRow(tr("Filtre (expression QGIS, optionnel)"), filter_row)
        layout.addLayout(form)

        x_label = QLabel(tr("Champs X (cochez 1 ou plusieurs ; le premier de la liste est l'axe, "
                            "les suivants forment les séries ; glissez pour réordonner)"))
        x_label.setWordWrap(True)
        layout.addWidget(x_label)
        self.x_list = QListWidget()
        self.x_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        layout.addWidget(self.x_list, 1)

        form2 = QFormLayout()
        self.y_combo = QComboBox()
        self.agg_combo = _combo(AGG_LABELS)
        self.sort_combo = _combo(SORT_LABELS)
        form2.addRow(tr("Champ Y"), self.y_combo)
        form2.addRow(tr("Calcul"), self.agg_combo)
        form2.addRow(tr("Tri de l'axe X"), self.sort_combo)
        layout.addLayout(form2)

        self.batch_group = QGroupBox(tr("Un graphique par valeur d'un champ (lot)"))
        batch_form = QFormLayout(self.batch_group)
        self.batch_combo = QComboBox()
        self.include_global = QCheckBox(tr("Ajouter un graphique global (toutes les valeurs)"))
        self.include_global.setChecked(True)
        self.global_label = QLineEdit("TOTAL")
        self.ignore_edit = QLineEdit()
        batch_form.addRow(self.batch_combo)
        batch_form.addRow(self.include_global)
        batch_form.addRow(tr("Libellé du graphique global"), self.global_label)
        batch_form.addRow(tr("Valeurs à ignorer (séparées par ;)"), self.ignore_edit)
        layout.addWidget(self.batch_group)

        self.spatial_group = QGroupBox(tr("Rattachement spatial à un territoire"))
        spatial_form = QFormLayout(self.spatial_group)
        self.spatial_check = QCheckBox(tr("Associer les entités à une couche polygonale"))
        self.polygon_combo = QComboBox()
        self.polygon_field_combo = QComboBox()
        self.hors_zone_check = QCheckBox(tr("Créer un graphique HORS_ZONE"))
        self.hors_zone_check.setChecked(True)
        self.csv_check = QCheckBox(tr("Exporter les entités HORS_ZONE en CSV"))
        spatial_form.addRow(self.spatial_check)
        spatial_form.addRow(tr("Couche polygonale"), self.polygon_combo)
        spatial_form.addRow(tr("Champ identifiant / libellé"), self.polygon_field_combo)
        spatial_form.addRow(self.hors_zone_check)
        spatial_form.addRow(self.csv_check)
        layout.addWidget(self.spatial_group)

        self.layer_combo.currentIndexChanged.connect(self._populate_fields)
        self.polygon_combo.currentIndexChanged.connect(self._populate_polygon_fields)
        self.spatial_check.toggled.connect(self._update_visibility)
        self.refresh_button.clicked.connect(self.refresh_layers)
        self.batch_combo.currentIndexChanged.connect(self._update_visibility)
        self.agg_combo.currentIndexChanged.connect(self._update_visibility)
        return page

    def _build_chart_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.type_combo = _combo(CHART_LABELS)
        self.title_edit = QLineEdit()
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        form.addRow(tr("Type de graphique"), self.type_combo)
        form.addRow(tr("Titre"), self.title_edit)
        form.addRow(tr("Libellé de l'axe X"), self.xlabel_edit)
        form.addRow(tr("Libellé de l'axe Y"), self.ylabel_edit)
        layout.addLayout(form)

        scales = QGroupBox(tr("Échelles (vide = automatique)"))
        scale_form = QFormLayout(scales)
        self.xmin_edit, self.xmax_edit = QLineEdit(), QLineEdit()
        self.ymin_edit, self.ymax_edit = QLineEdit(), QLineEdit()
        for edit in (self.xmin_edit, self.xmax_edit, self.ymin_edit, self.ymax_edit):
            edit.setPlaceholderText("auto")
        scale_form.addRow(tr("X min"), self.xmin_edit)
        scale_form.addRow(tr("X max"), self.xmax_edit)
        self.detect_x_button = QPushButton(tr("Détecter les bornes X"))
        self.detect_x_button.setToolTip(tr("Calcule les bornes à partir des valeurs X réellement retenues après le filtre."))
        self.detect_x_button.clicked.connect(self._detect_x_range)
        scale_form.addRow(self.detect_x_button)
        scale_form.addRow(tr("Y min"), self.ymin_edit)
        scale_form.addRow(tr("Y max"), self.ymax_edit)
        hint = QLabel(tr("Pour un X numérique, les données hors de la plage X sont ignorées."))
        hint.setWordWrap(True)
        scale_form.addRow(hint)
        layout.addWidget(scales)

        form2 = QFormLayout()
        self.color_button = QPushButton(tr("Choisir…"))
        self.color_button.clicked.connect(self._choose_color)
        self._apply_color_style()
        self.bins_spin = QSpinBox()
        self.bins_spin.setRange(1, 200)
        self.bins_spin.setValue(10)
        self.rotation_spin = QSpinBox()
        self.rotation_spin.setRange(0, 90)
        self.rotation_spin.setSingleStep(15)
        form2.addRow(tr("Couleur"), self.color_button)
        self.bins_label = QLabel(tr("Classes (histogramme)"))
        form2.addRow(self.bins_label, self.bins_spin)
        form2.addRow(tr("Rotation des étiquettes X"), self.rotation_spin)
        layout.addLayout(form2)
        self.series_color_list = QListWidget()
        self.series_color_list.setMaximumHeight(120)
        self.series_color_list.setToolTip(tr("Double-cliquez sur une série pour choisir sa couleur."))
        self.series_color_list.itemDoubleClicked.connect(self._choose_series_color)
        layout.addWidget(QLabel(tr("Couleurs des séries (après aperçu)")))
        layout.addWidget(self.series_color_list)

        self.legend_check = QCheckBox(tr("Légende"))
        self.legend_check.setChecked(True)
        self.grid_check = QCheckBox(tr("Grille"))
        self.values_check = QCheckBox(tr("Afficher les valeurs"))
        self.spines_check = QCheckBox(tr("Masquer le cadre haut et droite"))
        self.spines_check.setChecked(True)
        self.intY_check = QCheckBox(tr("Graduations entières sur Y"))
        self.intY_check.setChecked(True)
        self.allticks_check = QCheckBox(tr("Toutes les graduations sur X"))
        self.allticks_check.setChecked(True)
        for box in (self.legend_check, self.grid_check, self.values_check, self.spines_check,
                    self.intY_check, self.allticks_check):
            layout.addWidget(box)
        layout.addStretch(1)
        self.type_combo.currentIndexChanged.connect(self._update_visibility)
        self.type_combo.currentIndexChanged.connect(self._update_filename_preview)
        self.y_combo.currentIndexChanged.connect(self._update_filename_preview)
        self.x_list.itemChanged.connect(self._update_filename_preview)
        for edit in (self.xmin_edit, self.xmax_edit):
            edit.textChanged.connect(self._update_filename_preview)
        return page

    def _build_export_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText(tr("Choisir le dossier de sortie…"))
        self.browse_button = QPushButton(tr("Parcourir…"))
        self.browse_button.clicked.connect(self._browse)
        row.addWidget(self.folder_edit, 1)
        row.addWidget(self.browse_button)
        form.addRow(tr("Dossier de sortie"), row)

        self.pattern_combo = QComboBox()
        self.pattern_combo.setEditable(True)
        for preset in PRESET_NAMES:
            self.pattern_combo.addItem(preset)
        self.pattern_combo.setCurrentText(PRESET_NAMES[1])
        self.pattern_combo.setToolTip(tr("Préréglage de nom : équivalent du script Drainage")
                                      + " : " + PRESET_NAMES[0])
        form.addRow(tr("Nom des fichiers"), self.pattern_combo)
        self.filename_preview = QLabel()
        self.filename_preview.setWordWrap(True)
        form.addRow(tr("Aperçu du nom"), self.filename_preview)
        self.pattern_combo.currentTextChanged.connect(self._update_filename_preview)
        self.format_combo = _combo(FORMAT_LABELS)
        self.format_combo.currentIndexChanged.connect(self._update_filename_preview)
        form.addRow(tr("Format"), self.format_combo)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(200)
        self.width_spin = QDoubleSpinBox()
        self.height_spin = QDoubleSpinBox()
        for spin, value in ((self.width_spin, 5.85), (self.height_spin, 4.13)):
            spin.setRange(1.0, 40.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.5)
            spin.setValue(value)
        form.addRow(tr("Résolution (dpi)"), self.dpi_spin)
        form.addRow(tr("Largeur (pouces)"), self.width_spin)
        form.addRow(tr("Hauteur (pouces)"), self.height_spin)
        layout.addLayout(form)
        help_label = QLabel(tr("Balises : {couche} {x} {y} {type} {agregation} {valeur} {xmin} "
                               "{xmax} {duree} {date} (AAAAMMJJ) {aamm} (ex. 2611). "
                               "L'extension est ajoutée automatiquement."))
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        layout.addStretch(1)
        return page

    def _detect_x_range(self):
        """Renseigne X min/max depuis les valeurs numériques après filtre et sélection."""
        layer = self._current_layer()
        x_fields = self._checked_x()
        if layer is None or not x_fields:
            self._warn(tr("Choisissez une couche et cochez au moins un champ X."))
            return
        axis = x_fields[0]
        try:
            rows = data.read_rows(
                layer, [axis], self.selected_only.isChecked(), self.filter_edit.text(),
                cancelled=lambda: self._cancel)
        except core.ChartError as error:
            self._warn(tr("Impossible de détecter les bornes X : %s") % error)
            return
        values = [core.to_number(row.get(axis)) for row in rows]
        values = [value for value in values if value is not None]
        if not values:
            self._warn(tr("Aucune valeur X numérique disponible après application du filtre."))
            return
        self.xmin_edit.setText(core.format_number(min(values)))
        self.xmax_edit.setText(core.format_number(max(values)))
        self._update_filename_preview()

    def _update_filename_preview(self, *_args):
        layer = self._current_layer()
        try:
            xmin = core.parse_optional_float(self.xmin_edit.text())
            xmax = core.parse_optional_float(self.xmax_edit.text())
        except core.ChartError:
            xmin = xmax = None
        spec = core.ChartSpec(
            chart_type=self.type_combo.currentData() or "bar", xmin=xmin, xmax=xmax)
        values = {
            "couche": layer.name() if layer else "couche",
            "x": "_".join(self._checked_x()) or "X",
            "y": self.y_combo.currentData() or "NB",
            "type": spec.chart_type, "agregation": self.agg_combo.currentData() or "sum",
            "valeur": "HORS_ZONE" if self.spatial_check.isChecked() else "VALEUR",
            "xmin": core.format_number(spec.xmin), "xmax": core.format_number(spec.xmax),
            "duree": core.duration(spec.xmin, spec.xmax),
            "date": datetime.now().strftime("%Y%m%d"), "aamm": datetime.now().strftime("%y%m"),
        }
        extension = self.format_combo.currentData() or "png"
        try:
            name = core.build_filename(self.pattern_combo.currentText(), values, extension)
        except core.ChartError:
            name = ""
        self.filename_preview.setText(name)

    def _build_preview_pane(self):
        pane = QWidget()
        layout = QVBoxLayout(pane)
        row = QHBoxLayout()
        self.preview_value_label = QLabel(tr("Aperçu pour"))
        self.preview_value = QComboBox()
        row.addWidget(self.preview_value_label)
        row.addWidget(self.preview_value, 1)
        layout.addLayout(row)
        self.preview_label = QLabel(tr("Cliquez sur « Aperçu » pour afficher le graphique."))
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.preview_label)
        layout.addWidget(self.scroll, 1)
        return pane

    # ------------------------------------------------------------------ état de l'interface
    def _update_visibility(self, *_args):
        chart_type = self.type_combo.currentData()
        self.bins_spin.setVisible(chart_type == "hist")
        self.bins_label.setVisible(chart_type == "hist")
        spatial_on = self.spatial_check.isChecked()
        batch_on = bool(self.batch_combo.currentData()) and not spatial_on
        group_on = batch_on or spatial_on
        self.batch_combo.setEnabled(not spatial_on)
        for widget in (self.include_global, self.global_label, self.ignore_edit):
            widget.setEnabled(group_on)
        self.preview_value.setVisible(group_on)
        self.preview_value_label.setVisible(group_on)
        for widget in (self.polygon_combo, self.polygon_field_combo,
                       self.hors_zone_check, self.csv_check):
            widget.setEnabled(spatial_on)

    def _apply_color_style(self):
        self.color_button.setStyleSheet(f"background-color: {self._color};")

    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self._color), self)
        if color.isValid():
            self._color = core.valid_color(color.name())
            self._apply_color_style()

    def _choose_series_color(self, item):
        name = item.data(Qt.ItemDataRole.UserRole)
        current = self._series_colors.get(name, item.background().color().name())
        color = QColorDialog.getColor(QColor(current), self)
        if color.isValid():
            self._series_colors[name] = core.valid_color(color.name())
            item.setBackground(QColor(color.name()))

    def _request_cancel(self):
        self._cancel = True

    def _warn(self, message):
        QMessageBox.warning(self, tr("Attention"), message)

    def _open_expression_builder(self):
        layer = self._current_layer()
        if layer is None:
            self._warn(tr("Choisissez d'abord une couche vectorielle."))
            return
        builder = QgsExpressionBuilderDialog(layer, self.filter_edit.text(), self)
        execute = getattr(builder, "exec", None) or getattr(builder, "exec_", None)
        if execute and execute():
            self.filter_edit.setText(builder.expressionText())

    # ------------------------------------------------------------------ couches et champs
    def refresh_layers(self):
        previous = self.layer_combo.currentData()
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.layer_combo.addItem(layer.name(), layer.id())
        index = self.layer_combo.findData(previous) if previous else -1
        self.layer_combo.setCurrentIndex(index if index >= 0 else 0)
        self.layer_combo.blockSignals(False)
        self._populate_fields()
        self._populate_spatial_layers()

    def _populate_spatial_layers(self, *_args):
        previous = self.polygon_combo.currentData()
        self.polygon_combo.blockSignals(True)
        self.polygon_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and getattr(layer, "geometryType", lambda: -1)() == 2:
                self.polygon_combo.addItem(layer.name(), layer.id())
        index = self.polygon_combo.findData(previous) if previous else -1
        self.polygon_combo.setCurrentIndex(index if index >= 0 else 0)
        self.polygon_combo.blockSignals(False)
        self._populate_polygon_fields()

    def _polygon_layer(self):
        layer_id = self.polygon_combo.currentData()
        layer = QgsProject.instance().mapLayer(layer_id) if layer_id else None
        return layer if isinstance(layer, QgsVectorLayer) and getattr(layer, "geometryType", lambda: -1)() == 2 else None

    def _populate_polygon_fields(self, *_args):
        layer = self._polygon_layer()
        previous = self.polygon_field_combo.currentData()
        self.polygon_field_combo.clear()
        if layer is not None:
            for name in data.field_names(layer):
                self.polygon_field_combo.addItem(name, name)
        index = self.polygon_field_combo.findData(previous) if previous else -1
        self.polygon_field_combo.setCurrentIndex(index if index >= 0 else 0)

    def _current_layer(self):
        layer_id = self.layer_combo.currentData()
        layer = QgsProject.instance().mapLayer(layer_id) if layer_id else None
        return layer if isinstance(layer, QgsVectorLayer) else None

    def _checked_x(self):
        return [self.x_list.item(i).text() for i in range(self.x_list.count())
                if self.x_list.item(i).checkState() == Qt.CheckState.Checked]

    def _populate_fields(self, *_args):
        layer = self._current_layer()
        names = data.field_names(layer) if layer is not None else []
        kept_x = set(self._checked_x())
        kept_y = self.y_combo.currentData()
        kept_batch = self.batch_combo.currentData()

        self.x_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in kept_x else Qt.CheckState.Unchecked)
            self.x_list.addItem(item)

        self.y_combo.clear()
        self.y_combo.addItem(tr("— Nombre d'entités —"), NO_FIELD)
        self.batch_combo.clear()
        self.batch_combo.addItem(tr("— Un seul graphique —"), NO_FIELD)
        for name in names:
            self.y_combo.addItem(name, name)
            self.batch_combo.addItem(name, name)
        for combo, wanted in ((self.y_combo, kept_y), (self.batch_combo, kept_batch)):
            index = combo.findData(wanted) if wanted else 0
            combo.setCurrentIndex(index if index >= 0 else 0)
        self.preview_value.clear()
        self._update_visibility()
        self._update_filename_preview()

    # ------------------------------------------------------------------ lecture des réglages
    def _gather(self, need_output):
        """Valide les réglages ; retourne un dictionnaire, ou None après avoir prévenu."""
        layer = self._current_layer()
        if layer is None:
            self._warn(tr("Choisissez d'abord une couche vectorielle."))
            return None
        chart_type = self.type_combo.currentData()
        x_fields = self._checked_x()
        y_field = self.y_combo.currentData()
        how = self.agg_combo.currentData()
        if chart_type == "hist":
            if not y_field:
                self._warn(tr("L'histogramme de distribution demande un champ Y."))
                return None
        elif not x_fields:
            self._warn(tr("Cochez au moins un champ X (sauf pour un histogramme de distribution)."))
            return None
        if how not in ("count",) and not y_field and chart_type != "hist":
            how = "count"
        try:
            scales = [core.parse_optional_float(edit.text()) for edit in
                      (self.xmin_edit, self.xmax_edit, self.ymin_edit, self.ymax_edit)]
        except core.ChartError as error:
            self._warn(tr("Valeur invalide pour l'échelle : %s") % error)
            return None
        message = data.check_expression(self.filter_edit.text())
        if message:
            self._warn(tr("Expression invalide : %s") % message)
            return None
        spatial = self.spatial_check.isChecked()
        polygon_layer = self._polygon_layer() if spatial else None
        polygon_field = self.polygon_field_combo.currentData() if spatial else None
        if spatial and (polygon_layer is None or not polygon_field):
            self._warn(tr("Choisissez une couche polygonale et son champ de libellé."))
            return None
        pattern = self.pattern_combo.currentText().strip()
        unknown = core.unknown_placeholders(pattern)
        if unknown:
            self._warn(tr("Balises inconnues dans le nom : %s") % ", ".join(unknown))
            return None
        folder = self.folder_edit.text().strip()
        if need_output and not folder:
            self._warn(tr("Choisissez un dossier de sortie."))
            return None

        spec = core.ChartSpec(
            chart_type=chart_type, title=self.title_edit.text().strip(),
            xlabel=self.xlabel_edit.text().strip(), ylabel=self.ylabel_edit.text().strip(),
            xmin=scales[0], xmax=scales[1], ymin=scales[2], ymax=scales[3],
            color=core.valid_color(self._color), series_colors=dict(self._series_colors), width=self.width_spin.value(),
            height=self.height_spin.value(), dpi=self.dpi_spin.value(),
            legend=self.legend_check.isChecked(), grid=self.grid_check.isChecked(),
            show_values=self.values_check.isChecked(), hide_spines=self.spines_check.isChecked(),
            integer_y=self.intY_check.isChecked(), all_xticks=self.allticks_check.isChecked(),
            rotation=self.rotation_spin.value(), bins=self.bins_spin.value())
        return {
            "layer": layer, "spec": spec, "x_fields": x_fields, "y_field": y_field, "how": how,
            "sort": self.sort_combo.currentData(), "batch": self.batch_combo.currentData(),
            "include_global": self.include_global.isChecked(),
            "global_label": self.global_label.text().strip() or "TOTAL",
            "ignore": [v for v in self.ignore_edit.text().split(";")],
            "folder": folder, "pattern": pattern, "fmt": self.format_combo.currentData(),
            "selected_only": self.selected_only.isChecked(),
            "expression": self.filter_edit.text().strip(),
            "spatial": spatial, "polygon_layer": polygon_layer, "polygon_field": polygon_field,
            "hors_zone_chart": self.hors_zone_check.isChecked(),
            "hors_zone_csv": self.csv_check.isChecked(),
        }

    def _plan(self, job):
        """Lit la couche et prépare les graphiques territoriaux."""
        fields = list(job["x_fields"]) + [job["y_field"], job["batch"]]
        if job["spatial"]:
            if job["hors_zone_csv"]:
                fields = data.field_names(job["layer"])
            rows, outside = data.read_rows_by_polygon(
                job["layer"], job["polygon_layer"], job["polygon_field"], fields,
                job["selected_only"], job["expression"], cancelled=lambda: self._cancel)
            self._last_unmatched = outside
            groups = core.split_by_value(rows, "__territoire__", job["include_global"],
                                         job["global_label"], job["ignore"])
            if job["hors_zone_chart"] and outside:
                groups.append(("HORS_ZONE", outside))
        else:
            rows = data.read_rows(job["layer"], fields, job["selected_only"], job["expression"],
                                  cancelled=lambda: self._cancel)
            self._last_unmatched = []
            groups = core.split_by_value(rows, job["batch"], job["include_global"],
                                         job["global_label"], job["ignore"])
        spec = job["spec"]
        plan = []
        for label, subset in groups:
            try:
                chart = core.build_chart_data(
                    subset, job["x_fields"], job["y_field"], job["how"], job["sort"],
                    spec.chart_type, xmin=spec.xmin, xmax=spec.xmax,
                    y_name=job["y_field"] or tr("Comptage"))
                plan.append((label, chart, ""))
            except core.ChartError as error:
                plan.append((label, None, str(error)))
        return plan

    # ------------------------------------------------------------------ aperçu
    def _preview(self):
        if not render.matplotlib_available():
            self._warn(tr("Matplotlib est introuvable dans cette installation de QGIS."))
            return
        job = self._gather(False)
        if job is None:
            return
        try:
            plan = self._plan(job)
        except core.ChartError as error:
            self._warn(str(error))
            return
        if not plan:
            self._warn(tr("Aucune donnée à tracer : %s") % "")
            return
        series_names = []
        for _label, chart_data, _error in plan:
            if chart_data is not None:
                for series in chart_data.series:
                    if series.name not in series_names:
                        series_names.append(series.name)
        self.series_color_list.clear()
        for index, name in enumerate(series_names):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            color = self._series_colors.get(name, render.PALETTE[index % len(render.PALETTE)])
            item.setBackground(QColor(color))
            self.series_color_list.addItem(item)
        job["spec"].series_colors = dict(self._series_colors)
        wanted = self.preview_value.currentText()
        self.preview_value.blockSignals(True)
        self.preview_value.clear()
        for label, _chart, _error in plan:
            self.preview_value.addItem(label or tr("(global)"))
        index = self.preview_value.findText(wanted) if wanted else -1
        self.preview_value.setCurrentIndex(index if index >= 0 else 0)
        self.preview_value.blockSignals(False)
        label, chart, error = plan[self.preview_value.currentIndex()]
        if chart is None:
            self._warn(tr("Aucune donnée à tracer : %s") % error)
            return
        try:
            png = render.render_png_bytes(chart, job["spec"])
        except core.ChartError as error:
            self._warn(tr("Aucune donnée à tracer : %s") % error)
            return
        pixmap = QPixmap()
        pixmap.loadFromData(png)
        self._pixmap = pixmap
        self._update_pixmap()

    def _update_pixmap(self):
        if self._pixmap is None or self._pixmap.isNull():
            return
        width = max(200, self.scroll.viewport().width() - 8)
        shown = self._pixmap.scaledToWidth(min(width, self._pixmap.width()),
                                           Qt.TransformationMode.SmoothTransformation)
        self.preview_label.setPixmap(shown)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._update_pixmap()

    # ------------------------------------------------------------------ export
    def _browse(self):
        start = self.folder_edit.text().strip() or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, tr("Choisir le dossier de sortie…"), start)
        if folder:
            self.folder_edit.setText(folder)

    def _file_values(self, job, label, chart_spec):
        now = datetime.now()
        return {
            "couche": job["layer"].name(), "x": "_".join(job["x_fields"]),
            "y": job["y_field"] or "NB", "type": chart_spec.chart_type, "agregation": job["how"],
            "valeur": label, "xmin": core.format_number(chart_spec.xmin),
            "xmax": core.format_number(chart_spec.xmax),
            "duree": core.duration(chart_spec.xmin, chart_spec.xmax),
            "date": now.strftime("%Y%m%d"), "aamm": now.strftime("%y%m"),
        }

    def _export(self):
        if self._running:
            return
        if not render.matplotlib_available():
            self._warn(tr("Matplotlib est introuvable dans cette installation de QGIS."))
            return
        job = self._gather(True)
        if job is None:
            return
        self._running = True
        self._cancel = False
        self._set_busy(True)
        try:
            self._run_export(job)
        finally:
            self._running = False
            self._set_busy(False)

    def _set_busy(self, busy):
        for button in (self.export_button, self.preview_button, self.close_button):
            button.setEnabled(not busy)
        self.cancel_button.setVisible(busy)
        self.progress.setVisible(busy)
        if busy:
            self.progress.setRange(0, 0)
        QApplication.processEvents()

    def _run_export(self, job):
        folder = os.path.abspath(job["folder"])
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as error:
            self._warn(tr("Impossible de créer le dossier : %s") % error)
            return
        try:
            plan = self._plan(job)
        except core.ChartError as error:
            if self._cancel:
                QMessageBox.information(self, tr("Information"), tr("Export annulé."))
            else:
                self._warn(str(error))
            return

        items = [(label, chart) for label, chart, _error in plan if chart is not None]
        skipped = [label or tr("(global)") for label, chart, _error in plan if chart is None]
        if not items and not (job["spatial"] and job["hors_zone_csv"] and self._last_unmatched):
            self._warn(tr("Aucune donnée à tracer : %s") % ", ".join(e for _l, c, e in plan if c is None))
            return
        spec = job["spec"]
        names = core.unique_names([
            core.build_filename(job["pattern"], self._file_values(job, label, spec), job["fmt"])
            for label, _chart in items])
        targets = [os.path.join(folder, name) for name in names]
        csv_target = None
        if job["spatial"] and job["hors_zone_csv"] and self._last_unmatched:
            csv_target = os.path.join(
                folder, core.build_filename(job["pattern"], self._file_values(job, "HORS_ZONE", spec), "csv"))
        existing = [t for t in targets if os.path.exists(t)]
        if csv_target and os.path.exists(csv_target):
            existing.append(csv_target)
        if existing:
            answer = QMessageBox.question(
                self, tr("Attention"), tr("%d fichier(s) existent déjà. Les écraser ?") % len(existing),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.progress.setRange(0, len(items))
        done = 0
        for (label, chart), target in zip(items, targets):
            QApplication.processEvents()
            if self._cancel:
                QMessageBox.information(self, tr("Information"), tr("Export annulé."))
                return
            try:
                render.save_chart(chart, spec, target, job["fmt"])
            except (OSError, core.ChartError) as error:
                self._warn(tr("Erreur d'écriture : %s") % error)
                return
            done += 1
            self.progress.setValue(done)
        csv_done = False
        if csv_target:
            try:
                attribute_fields = list(dict.fromkeys(
                    key for row in self._last_unmatched for key in row.keys()
                    if not key.startswith("__")))
                csv_fields = ["ID_SOURCE", "MOTIF"] + attribute_fields
                with open(csv_target, "w", newline="", encoding="utf-8-sig") as stream:
                    writer = csv.DictWriter(stream, fieldnames=csv_fields, extrasaction="ignore",
                                            delimiter=";")
                    writer.writeheader()
                    for row in self._last_unmatched:
                        record = {"ID_SOURCE": row.get("__fid__"), "MOTIF": row.get("__motif__")}
                        record.update({key: row.get(key) for key in attribute_fields})
                        writer.writerow(record)
                csv_done = True
            except OSError as error:
                self._warn(tr("Erreur d'écriture : %s") % error)
        message = tr("%d graphique(s) exporté(s) dans :\n%s") % (done, folder)
        if csv_done:
            message += "\nCSV HORS_ZONE : " + os.path.basename(csv_target)
        if skipped:
            message += "\n\n" + tr("%d graphique(s) ignoré(s) (aucune donnée) : %s") % (
                len(skipped), ", ".join(skipped))
        QMessageBox.information(self, tr("Information"), message)
        self._save_settings()

    # ------------------------------------------------------------------ mémorisation
    def _save_settings(self):
        settings = QgsSettings()
        values = {
            "folder": self.folder_edit.text(), "pattern": self.pattern_combo.currentText(),
            "format": self.format_combo.currentData(), "dpi": self.dpi_spin.value(),
            "width": self.width_spin.value(), "height": self.height_spin.value(),
            "type": self.type_combo.currentData(), "agg": self.agg_combo.currentData(),
            "sort": self.sort_combo.currentData(), "color": self._color,
            "legend": self.legend_check.isChecked(), "grid": self.grid_check.isChecked(),
            "values": self.values_check.isChecked(), "spines": self.spines_check.isChecked(),
            "inty": self.intY_check.isChecked(), "allticks": self.allticks_check.isChecked(),
            "global_label": self.global_label.text(), "include_global": self.include_global.isChecked(),
            "spatial": self.spatial_check.isChecked(), "hors_zone_chart": self.hors_zone_check.isChecked(),
            "hors_zone_csv": self.csv_check.isChecked(),
        }
        for key, value in values.items():
            settings.setValue(SETTINGS_PREFIX + key, value)

    def _load_settings(self):
        settings = QgsSettings()

        def get(key, default, kind=str):
            value = settings.value(SETTINGS_PREFIX + key, default)
            if kind is bool:
                return value in (True, "true", "True", 1, "1")
            try:
                return kind(value)
            except (TypeError, ValueError):
                return default

        self.folder_edit.setText(get("folder", ""))
        self.pattern_combo.setCurrentText(get("pattern", PRESET_NAMES[1]))
        for combo, key in ((self.format_combo, "format"), (self.type_combo, "type"),
                           (self.agg_combo, "agg"), (self.sort_combo, "sort")):
            index = combo.findData(get(key, ""))
            if index >= 0:
                combo.setCurrentIndex(index)
        self.dpi_spin.setValue(get("dpi", 200, int))
        self.width_spin.setValue(get("width", 5.85, float))
        self.height_spin.setValue(get("height", 4.13, float))
        self._color = core.valid_color(get("color", core.DEFAULT_COLOR))
        self._apply_color_style()
        self.legend_check.setChecked(get("legend", True, bool))
        self.grid_check.setChecked(get("grid", False, bool))
        self.values_check.setChecked(get("values", False, bool))
        self.spines_check.setChecked(get("spines", True, bool))
        self.intY_check.setChecked(get("inty", True, bool))
        self.allticks_check.setChecked(get("allticks", True, bool))
        self.global_label.setText(get("global_label", "TOTAL"))
        self.include_global.setChecked(get("include_global", True, bool))
        self.spatial_check.setChecked(get("spatial", False, bool))
        self.hors_zone_check.setChecked(get("hors_zone_chart", True, bool))
        self.csv_check.setChecked(get("hors_zone_csv", False, bool))
        self._update_visibility()

    def closeEvent(self, event):  # noqa: N802
        if self._running:
            self._cancel = True
        self._save_settings()
        super().closeEvent(event)
