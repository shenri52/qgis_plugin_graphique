# -*- coding: utf-8 -*-
"""Test d'intégration de la fenêtre avec une vraie pile Qt : python qt_smoke.py PyQt5|PyQt6 fr|en"""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MPLBACKEND"] = "Agg"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

QT, LANG = sys.argv[1], sys.argv[2]
FRENCH = LANG == "fr"
import qgis_stubs  # noqa: E402
mods = qgis_stubs.install(QT)

from qgis_plugin_graphique import core, dialog, i18n, plugin as plugin_mod  # noqa: E402

failures = []


def check(condition, message):
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        failures.append(message)


app = mods["QtWidgets"].QApplication([])
Qt = mods["QtCore"].Qt
STD = mods["QtWidgets"].QMessageBox.StandardButton
LOG = {"warning": [], "information": [], "question": []}
ANSWER = {"question": "yes", "folder": ""}


class FakeMessageBox(mods["QtWidgets"].QMessageBox):
    @staticmethod
    def warning(_parent, _title, text, *a):
        LOG["warning"].append(text)

    @staticmethod
    def information(_parent, _title, text, *a):
        LOG["information"].append(text)

    @staticmethod
    def question(_parent, _title, text, buttons, default):
        LOG["question"].append(text)
        return STD.Yes if ANSWER["question"] == "yes" else STD.No


class FakeFileDialog:
    @staticmethod
    def getExistingDirectory(*_a):  # noqa: N802
        return ANSWER["folder"]


dialog.QMessageBox = FakeMessageBox
dialog.QFileDialog = FakeFileDialog
dialog.tr = lambda text, french=None: i18n.tr(text, FRENCH)
i18n_is_french = lambda: FRENCH  # noqa: E731
i18n.is_french = i18n_is_french


def reset():
    for key in LOG:
        LOG[key].clear()


def set_x(dlg, names):
    for i in range(dlg.x_list.count()):
        item = dlg.x_list.item(i)
        item.setCheckState(Qt.CheckState.Checked if item.text() in names else Qt.CheckState.Unchecked)


def select(combo, key):
    index = combo.findData(key)
    assert index >= 0, key
    combo.setCurrentIndex(index)


root = tempfile.mkdtemp(prefix="graph_smoke_")
OUT = os.path.join(root, "graph")
NULL = qgis_stubs.NULL
records = []
for i in range(30):
    records.append({"DATE": 2016 + i % 10, "SIREN": ["2001", "2002", "2003"][i % 3],
                    "HA": float(i + 1) if i != 4 else NULL, "TXT": "t" if i % 2 else NULL})
layer = qgis_stubs.QgsVectorLayer("Drainage", ["DATE", "SIREN", "HA", "TXT"], records, selected=[0, 1, 2])
project = qgis_stubs.FakeProject.instance()
project.layers[layer.id()] = layer
project.layers["not_vector"] = object()
qgis_stubs.FakeSettings.store.clear()

print(f"== {QT} / interface {'FR' if FRENCH else 'EN'} ==")
dlg = dialog.GraphDialog()
check(dlg.layer_combo.count() == 1 and dlg.layer_combo.currentText() == "Drainage", "seules les couches vectorielles sont listées")
check([dlg.x_list.item(i).text() for i in range(dlg.x_list.count())] == ["DATE", "SIREN", "HA", "TXT"], "champs listés")
check(dlg.y_combo.count() == 5 and dlg.y_combo.currentData() == "", "Y : champs + « nombre d'entités »")
check(dlg.type_combo.count() == 8 and dlg.agg_combo.count() == 7 and dlg.format_combo.count() == 5, "types, calculs et formats")
check(dlg.tabs.count() == 3, "3 onglets")
check(dlg.windowTitle() == ("Graphique Couche" if FRENCH else "Layer Chart"), "titre localisé")
check(dlg.bins_spin.isHidden() and not dlg.include_global.isEnabled(), "classes et lot masqués/inactifs par défaut")

# ---- validations
reset()
dlg._preview()
check(len(LOG["warning"]) == 1, "aperçu sans champ X refusé")
set_x(dlg, ["DATE"])
dlg.xmin_edit.setText("abc")
reset()
dlg._preview()
check(len(LOG["warning"]) == 1, "échelle invalide refusée")
dlg.xmin_edit.setText("")
dlg.filter_edit.setText('("DATE" >= ')
reset()
dlg._preview()
check(len(LOG["warning"]) == 1, "expression invalide refusée")
dlg.filter_edit.setText("")
dlg.pattern_combo.setCurrentText("{bidon}")
reset()
dlg._export()
check(len(LOG["warning"]) == 1 and not LOG["information"], "balise inconnue refusée")
dlg.pattern_combo.setCurrentText(i18n.PRESET_NAMES[0])
reset()
dlg._export()
check(len(LOG["warning"]) == 1, "export sans dossier refusé")

# ---- aperçu
select(dlg.y_combo, "HA")
select(dlg.agg_combo, "sum")
dlg.title_edit.setText("Mon titre")
dlg.xmin_edit.setText("2020")
dlg.xmax_edit.setText("2024")
reset()
dlg._preview()
check(not LOG["warning"] and dlg._pixmap is not None and not dlg._pixmap.isNull(), "aperçu : image produite")
check(dlg.preview_label.pixmap() is not None, "aperçu affiché")
select(dlg.type_combo, "hist")
check(not dlg.bins_spin.isHidden() or dlg.bins_spin.isVisibleTo(dlg), "histogramme : réglage des classes visible")
reset()
dlg._preview()
check(not LOG["warning"], "aperçu de l'histogramme de distribution")
select(dlg.type_combo, "bar")

# ---- export simple : reproduit le nommage du script (valeur de lot absente)
dlg.folder_edit.setText(OUT)
dlg.pattern_combo.setCurrentText("{y}_{duree}Ans")
reset()
dlg._export()
check(os.path.isfile(os.path.join(OUT, "HA_5Ans.png")) and len(LOG["information"]) == 1, "export simple : HA_5Ans.png dans le dossier créé")

# ---- lot : un graphique par SIREN + global, comme le script
select(dlg.batch_combo, "SIREN")
check(dlg.include_global.isEnabled(), "lot actif")
dlg.global_label.setText("DEPARTEMENT")
dlg.pattern_combo.setCurrentText("{y}_{duree}Ans_{valeur}")
select(dlg.y_combo, "")
reset()
dlg._export()
expected = {f"NB_5Ans_{v}.png" for v in ("2001", "2002", "2003", "DEPARTEMENT")}
check(expected <= set(os.listdir(OUT)), f"lot : fichiers {sorted(expected)}")
check(LOG["information"] and "4" in LOG["information"][0], "message final : 4 graphiques")

# ---- ignorer une valeur + sans global
dlg.ignore_edit.setText("2002; 2003")
dlg.include_global.setChecked(False)
dlg.pattern_combo.setCurrentText("seul_{valeur}")
reset()
dlg._export()
check(os.path.isfile(os.path.join(OUT, "seul_2001.png")) and not os.path.exists(os.path.join(OUT, "seul_2002.png"))
      and not os.path.exists(os.path.join(OUT, "seul_DEPARTEMENT.png")), "valeurs ignorées, pas de global")
dlg.ignore_edit.setText("")
dlg.include_global.setChecked(True)

# ---- écrasement
reset()
ANSWER["question"] = "no"
dlg.pattern_combo.setCurrentText("{y}_{duree}Ans_{valeur}")
before = os.path.getmtime(os.path.join(OUT, "NB_5Ans_2001.png"))
dlg._export()
check(len(LOG["question"]) == 1 and not LOG["information"] and os.path.getmtime(os.path.join(OUT, "NB_5Ans_2001.png")) == before,
      "fichiers existants : confirmation, refus respecté")
ANSWER["question"] = "yes"
reset()
dlg._export()
check(len(LOG["question"]) == 1 and len(LOG["information"]) == 1, "confirmation acceptée : export refait")

# ---- formats, taille, noms identiques, sécurité du nom
for fmt in ("jpg", "svg", "pdf", "tiff"):
    select(dlg.format_combo, fmt)
    dlg.pattern_combo.setCurrentText("fmt")
    reset()
    dlg.batch_combo.setCurrentIndex(0)
    dlg._export()
    check(os.path.isfile(os.path.join(OUT, f"fmt.{fmt}")), f"format {fmt}")
select(dlg.format_combo, "png")
dlg.pattern_combo.setCurrentText("../../evil/{couche}")
reset()
dlg._export()
check(os.path.isfile(os.path.join(OUT, "evil" + "Drainage.png")) or os.path.isfile(os.path.join(OUT, "evilDrainage.png"))
      or any(n.startswith("evil") for n in os.listdir(OUT)), "nom avec ../ neutralisé : reste dans le dossier choisi")
check(not os.path.exists(os.path.join(root, "evil")), "aucun fichier hors du dossier de sortie")

# ---- plusieurs X : séries empilées
set_x(dlg, ["DATE", "SIREN"])
select(dlg.type_combo, "stacked")
select(dlg.y_combo, "HA")
dlg.xmin_edit.setText("")
dlg.xmax_edit.setText("")
dlg.pattern_combo.setCurrentText("stack")
reset()
dlg._export()
check(os.path.isfile(os.path.join(OUT, "stack.png")), "plusieurs champs X : barres empilées exportées")

# ---- sélection et filtre
set_x(dlg, ["DATE"])
select(dlg.type_combo, "bar")
dlg.selected_only.setChecked(True)
dlg.filter_edit.setText('"DATE" >= 2017')
rows = dialog.data.read_rows(layer, ["DATE"], True, '"DATE" >= 2017')
check(len(rows) == 2, "entités sélectionnées + expression : 2 lignes")
dlg.selected_only.setChecked(False)
dlg.filter_edit.setText("")

# ---- aucune donnée
dlg.xmin_edit.setText("3000")
dlg.xmax_edit.setText("3001")
dlg.pattern_combo.setCurrentText("vide")
reset()
dlg._export()
check(len(LOG["warning"]) == 1 and not os.path.exists(os.path.join(OUT, "vide.png")), "aucune donnée : message, rien d'écrit")
dlg.xmin_edit.setText("")
dlg.xmax_edit.setText("")

# ---- annulation pendant l'export
dlg.batch_combo.setCurrentIndex(0)
dlg.pattern_combo.setCurrentText("annule")
original = dialog.render.save_chart


def cancelling(*args, **kwargs):
    dlg._cancel = True
    return original(*args, **kwargs)


dialog.render.save_chart = cancelling
reset()
dlg._export()
dialog.render.save_chart = original
check(len(LOG["information"]) == 1 and dlg.export_button.isEnabled() and not dlg._running, "annulation : interface réactivée")

# ---- parcourir, couleur, mémorisation
ANSWER["folder"] = os.path.join(root, "autre")
dlg._browse()
check(dlg.folder_edit.text() == ANSWER["folder"], "parcourir : dossier choisi")
dlg._color = "#112233"
dlg.pattern_combo.setCurrentText("memo")
dlg._save_settings()
dlg2 = dialog.GraphDialog()
check(dlg2.pattern_combo.currentText() == "memo" and dlg2._color == "#112233" and dlg2.folder_edit.text() == ANSWER["folder"],
      "réglages mémorisés")
check(dlg2.type_combo.currentData() == "bar" and dlg2.format_combo.currentData() == "png", "type et format mémorisés")

# ---- actualisation et couche supprimée
del project.layers[layer.id()]
dlg.refresh_layers()
check(dlg.layer_combo.count() == 0 and dlg.x_list.count() == 0, "couche retirée du projet : listes vidées")
reset()
dlg._preview()
check(len(LOG["warning"]) == 1, "sans couche : aperçu refusé")


# ---- plugin (menu + barre d'outils)
class FakeIface:
    def __init__(self):
        self.calls = []

    def mainWindow(self):  # noqa: N802
        return None

    def addPluginToMenu(self, menu, action):  # noqa: N802
        self.calls.append(("menu+", menu))

    def addToolBarIcon(self, action):  # noqa: N802
        self.calls.append(("toolbar+", action.text()))

    def removePluginMenu(self, menu, action):  # noqa: N802
        self.calls.append(("menu-", menu))

    def removeToolBarIcon(self, action):  # noqa: N802
        self.calls.append(("toolbar-",))


class FakeDialog:
    opened = 0
    closed = 0

    def __init__(self, parent=None):
        pass

    def show(self):
        FakeDialog.opened += 1

    def raise_(self):
        pass

    def activateWindow(self):  # noqa: N802
        pass

    def refresh_layers(self):
        pass

    def close(self):
        FakeDialog.closed += 1

    def deleteLater(self):  # noqa: N802
        pass


plugin_mod.GraphDialog = FakeDialog
plugin_mod.tr = lambda text, french=None: i18n.tr(text, FRENCH)
iface = FakeIface()
instance = plugin_mod.GraphiquePlugin(iface)
instance.initGui()
menu = "&Graphique Couche" if FRENCH else "&Layer Chart"
check(("menu+", menu) in iface.calls, "entrée dans le menu Extensions")
check(any(c[0] == "toolbar+" for c in iface.calls) and not instance.action.icon().isNull(), "icône dans la barre d'outils")
instance.action.trigger()
instance.action.trigger()
check(FakeDialog.opened == 2 and instance.dialog is not None, "clic : fenêtre affichée, instance réutilisée")
instance.unload()
check(("menu-", menu) in iface.calls and ("toolbar-",) in iface.calls and FakeDialog.closed == 1, "déchargement propre")

shutil.rmtree(root, ignore_errors=True)
print(f"-- {len(failures)} échec(s)")
sys.exit(1 if failures else 0)
