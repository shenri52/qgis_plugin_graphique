# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtGui import QAction, QIcon

from .dialog import GraphDialog
from .i18n import tr


class GraphiquePlugin:
    """Plugin QGIS autonome : entrée dans Extensions et icône de barre d'outils."""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):  # noqa: N802
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
        self.action = QAction(icon, tr("Graphique Couche"), self.iface.mainWindow())
        self.action.setObjectName("GraphiqueCoucheAction")
        self.action.setToolTip(tr("Créer et exporter un graphique à partir d'une couche"))
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(tr("&Graphique Couche"), self.action)
        self.iface.addToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = GraphDialog(self.iface.mainWindow() if self.iface else None)
        else:
            self.dialog.refresh_layers()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(tr("&Graphique Couche"), self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
