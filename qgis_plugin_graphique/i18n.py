# -*- coding: utf-8 -*-
"""Textes de l'interface : français si QGIS est en français, anglais sinon."""

EN = {
    "Graphique Couche": "Layer Chart",
    "&Graphique Couche": "&Layer Chart",
    "Créer et exporter un graphique à partir d'une couche": "Create and export a chart from a layer",
    "Aperçu": "Preview",
    "Exporter": "Export",
    "Fermer": "Close",
    "Réinitialiser les paramètres": "Reset settings",
    "Tous les paramètres seront remis à leurs valeurs par défaut. Continuer ?":
        "All settings will be restored to their defaults. Continue?",
    "Données": "Data",
    "Graphique": "Chart",
    "Export": "Export",
    "Couche": "Layer",
    "Actualiser la liste des couches": "Refresh layer list",
    "Entités sélectionnées uniquement": "Selected features only",
    "Filtre (expression QGIS, optionnel)": "Filter (QGIS expression, optional)",
    "Constructeur…": "Expression builder…",
    "Aperçu du nom": "File name preview",
    "Couche polygonale": "Polygon layer",
    "Champ identifiant / libellé": "Identifier / label field",
    "Rattachement spatial à un territoire": "Spatial assignment to a territory",
    "Associer les entités à une couche polygonale": "Assign features to a polygon layer",
    "Créer un graphique HORS_ZONE": "Create an OUT_OF_AREA chart",
    "Exporter les entités HORS_ZONE en CSV": "Export OUT_OF_AREA features to CSV",
    "Choisissez une couche polygonale et son champ de libellé.": "Choose a polygon layer and its label field.",
    "ex. \"DATE\" >= 2021": "e.g. \"DATE\" >= 2021",
    "Champs X (cochez 1 ou plusieurs ; le premier de la liste est l'axe, les suivants forment les séries ; glissez pour réordonner)":
        "X fields (tick 1 or more; the first in the list is the axis, the others form the series; drag to reorder)",
    "Champ Y": "Y field",
    "— Nombre d'entités —": "— Feature count —",
    "Calcul": "Calculation",
    "Somme": "Sum",
    "Moyenne": "Mean",
    "Médiane": "Median",
    "Minimum": "Minimum",
    "Maximum": "Maximum",
    "Comptage": "Count",
    "Aucun (une valeur par entité)": "None (one value per feature)",
    "Tri de l'axe X": "X axis order",
    "X croissant": "X ascending",
    "X décroissant": "X descending",
    "Ordre de la couche": "Layer order",
    "Y décroissant": "Y descending",
    "Un graphique par valeur d'un champ (lot)": "One chart per field value (batch)",
    "— Un seul graphique —": "— A single chart —",
    "Ajouter un graphique global (toutes les valeurs)": "Add a global chart (all values)",
    "Libellé du graphique global": "Global chart label",
    "Valeurs à ignorer (séparées par ;)": "Values to skip (separated by ;)",
    "Type de graphique": "Chart type",
    "Histogramme (barres)": "Bar chart",
    "Barres horizontales": "Horizontal bars",
    "Barres empilées": "Stacked bars",
    "Courbe": "Line",
    "Aire": "Area",
    "Nuage de points": "Scatter",
    "Camembert": "Pie",
    "Histogramme de distribution (champ Y)": "Distribution histogram (Y field)",
    "Titre": "Title",
    "Libellé de l'axe X": "X axis label",
    "Libellé de l'axe Y": "Y axis label",
    "Échelles (vide = automatique)": "Scales (empty = automatic)",
    "X min": "X min",
    "X max": "X max",
    "Détecter les bornes X": "Detect X range",
    "Calcule les bornes à partir des valeurs X réellement retenues après le filtre.":
        "Detects the range from X values retained after applying the filter.",
    "Choisissez une couche et cochez au moins un champ X.":
        "Choose a layer and tick at least one X field.",
    "Impossible de détecter les bornes X : %s": "Could not detect the X range: %s",
    "Aucune valeur X numérique disponible après application du filtre.":
        "No numeric X values are available after applying the filter.",
    "Y min": "Y min",
    "Y max": "Y max",
    "Pour un X numérique, les données hors de la plage X sont ignorées.":
        "For a numeric X, data outside the X range is ignored.",
    "Couleur": "Color",
    "Couleurs des séries (après aperçu)": "Series colours (after preview)",
    "Double-cliquez sur une série pour choisir sa couleur.": "Double-click a series to choose its colour.",
    "Choisir…": "Choose…",
    "Classes (histogramme)": "Bins (histogram)",
    "Rotation des étiquettes X": "X label rotation",
    "Légende": "Legend",
    "Grille": "Grid",
    "Afficher les valeurs": "Show values",
    "Masquer le cadre haut et droite": "Hide top and right frame",
    "Graduations entières sur Y": "Integer Y ticks",
    "Toutes les graduations sur X": "All X ticks",
    "Dossier de sortie": "Output folder",
    "Choisir le dossier de sortie…": "Choose the output folder…",
    "Parcourir…": "Browse…",
    "Nom des fichiers": "File name",
    "Balises : {couche} {x} {y} {type} {agregation} {valeur} {xmin} {xmax} {duree} {date} (AAAAMMJJ) "
    "{aamm} (ex. 2611). L'extension est ajoutée automatiquement.":
        "Tags: {couche} {x} {y} {type} {agregation} {valeur} {xmin} {xmax} {duree} {date} (YYYYMMDD) "
        "{aamm} (e.g. 2611). The extension is added automatically.",
    "Format": "Format",
    "Résolution (dpi)": "Resolution (dpi)",
    "Largeur (pouces)": "Width (inches)",
    "Hauteur (pouces)": "Height (inches)",
    "Aperçu pour": "Preview for",
    "Cliquez sur « Aperçu » pour afficher le graphique.": "Click “Preview” to display the chart.",
    "Choisissez d'abord une couche vectorielle.": "Choose a vector layer first.",
    "Cochez au moins un champ X (sauf pour un histogramme de distribution).":
        "Tick at least one X field (except for a distribution histogram).",
    "L'histogramme de distribution demande un champ Y.": "A distribution histogram needs a Y field.",
    "Valeur invalide pour l'échelle : %s": "Invalid scale value: %s",
    "Expression invalide : %s": "Invalid expression: %s",
    "Balises inconnues dans le nom : %s": "Unknown tags in the file name: %s",
    "Choisissez un dossier de sortie.": "Choose an output folder.",
    "Impossible de créer le dossier : %s": "Cannot create the folder: %s",
    "Aucune donnée à tracer : %s": "Nothing to plot: %s",
    "Matplotlib est introuvable dans cette installation de QGIS.":
        "Matplotlib was not found in this QGIS installation.",
    "%d fichier(s) existent déjà. Les écraser ?": "%d file(s) already exist. Overwrite them?",
    "%d graphique(s) exporté(s) dans :\n%s": "%d chart(s) exported to:\n%s",
    "%d graphique(s) ignoré(s) (aucune donnée) : %s": "%d chart(s) skipped (no data): %s",
    "Erreur d'écriture : %s": "Write error: %s",
    "Export annulé.": "Export cancelled.",
    "Annuler": "Cancel",
    "Attention": "Warning",
    "Information": "Information",
    "(global)": "(global)",
    "Préréglage de nom : équivalent du script Drainage": "Name preset: Drainage script equivalent",
}

PRESET_NAMES = (
    "{y}_{duree}Ans_{valeur}",
    "{couche}_{type}_{valeur}",
    "{couche}_{y}_par_{x}",
    "graphique_{date}",
)


def _safe(getter):
    """Appelle getter ; retourne None si l'API de langue n'est pas disponible."""
    try:
        return getter()
    except (AttributeError, RuntimeError, TypeError):
        return None


def is_french():
    """Détecte la langue configurée dans QGIS, puis celle du système."""
    try:
        from qgis.core import QgsApplication
        from qgis.PyQt.QtCore import QLocale
    except ImportError:
        return True
    candidates = (
        _safe(lambda: QgsApplication.locale()),
        _safe(lambda: QLocale().name()),
        _safe(lambda: QLocale.system().name()),
    )
    for candidate in candidates:
        if candidate:
            return str(candidate).replace("-", "_").lower().startswith("fr")
    return True


def tr(text, french=None):
    """Retourne le texte français tel quel, ou sa version anglaise."""
    if french is None:
        french = is_french()
    return text if french else EN.get(text, text)
