# Graphique Couche

[![QGIS](https://img.shields.io/badge/QGIS-3.28%2B-green)](https://qgis.org/)
[![Tests](https://github.com/shenri52/qgis_plugin_graphique/actions/workflows/tests.yml/badge.svg)](https://github.com/shenri52/qgis_plugin_graphique/actions/workflows/tests.yml)

## Français

**Graphique Couche** est une extension QGIS qui transforme la table attributaire de **n'importe quelle couche vectorielle** en graphique, avec aperçu, puis l'exporte en image. Elle est accessible depuis **Extensions → Graphique Couche** et depuis une icône de la barre d'outils.

Elle généralise un script de suivi du drainage (graphiques par EPCI et pour le département) : le script n'est plus lié à une couche ni à des noms de champs.

### Fonctionnalités

- Choix de la **couche**, des **champs X** (un ou plusieurs) et du **champ Y**. Le premier champ X coché de la liste est l'axe ; les suivants forment les séries (barres groupées/empilées, plusieurs courbes). Glissez les champs pour changer l'ordre.
- **Calcul** sur Y : somme, moyenne, médiane, minimum, maximum, comptage, ou aucune agrégation. Sans champ Y : comptage des entités.
- **Types** : histogramme (barres), barres horizontales, barres empilées, courbe, aire, nuage de points, camembert, histogramme de distribution.
- **Titre**, **libellés** des axes X et Y, **échelles min/max** (vide = automatique), détection des bornes X à partir des données après filtre et sélection (bouton dédié), couleur par série, légende, grille, valeurs affichées, rotation des étiquettes, graduations entières.
- Filtre par **expression QGIS** avec constructeur d'expression et option « entités sélectionnées uniquement ».
- **Couleurs individuelles des séries** configurables après l'aperçu.
- **Aperçu du nom de fichier** sous la formule de nommage.
- **Aperçu** dans la fenêtre avant export.
- **Export** dans le dossier de votre choix, en **PNG, JPEG, SVG, PDF ou TIFF**, avec résolution et taille réglables.
- **Mode lot** : un graphique par valeur d'un champ (ex. un par territoire), plus un graphique global optionnel, avec une liste de valeurs à ignorer.
- **Rattachement spatial facultatif** : associe chaque entité à une couche polygonale quelconque par plus grande surface d'intersection pour les sources polygonales, plus grande longueur d'intersection pour les sources linéaires, et point représentatif pour les sources ponctuelles (reprojection si nécessaire), sans créer ni modifier de champ dans la couche source. Les entités sans correspondance sont exclues du total territorial, peuvent produire un graphique `HORS_ZONE` et un CSV de contrôle. En cas de recouvrement, le polygone dont l'identifiant QGIS est le plus petit est retenu.
- **Nom des fichiers personnalisable** avec des balises. La balise `{duree}` est calculée à partir des bornes X ; le bouton « Détecter les bornes X » renseigne ces bornes depuis les valeurs numériques retenues après filtre et sélection (le filtre ne définit donc pas lui-même la durée). Balises disponibles : `{couche}` `{x}` `{y}` `{type}` `{agregation}` `{valeur}` `{xmin}` `{xmax}` `{duree}` `{date}` (AAAAMMJJ) `{aamm}` (ex. 2611). L'extension est ajoutée automatiquement ; les caractères dangereux (`/`, `\`, `..`) sont retirés ; deux noms identiques sont rendus uniques ; un fichier existant n'est écrasé qu'après confirmation.
- Interface en français ou en anglais selon la langue de QGIS ; réglages mémorisés.

### Installation

1. Téléchargez `qgis_plugin_graphique.zip` depuis la page [Releases](https://github.com/shenri52/qgis_plugin_graphique/releases).
2. Dans QGIS, ouvrez **Extensions → Installer/Gérer les extensions → Installer depuis un ZIP**.
3. Sélectionnez l'archive téléchargée.

Le plugin utilise **matplotlib**, fourni avec QGIS sous Windows et macOS. Sous Linux, installez le paquet `python3-matplotlib` s'il manque.

### Développement et tests

```bash
pip install -r requirements-dev.txt
python -m pytest test -q                 # logique, rendu, métadonnées, règles de sécurité
python test/qt_smoke.py PyQt6 fr         # fenêtre avec une vraie pile Qt (PyQt5 ou PyQt6, fr ou en)
bandit -r qgis_plugin_graphique -ll      # analyse de sécurité
```

Les tests tournent sans QGIS (un faux module `qgis` est fourni dans `test/qgis_stubs.py`). Ils ne remplacent pas un essai dans QGIS : testez toujours une version avant de la publier.

Publier une version : mettre à jour `version` et `changelog` dans `metadata.txt`, puis créer une release GitHub dont le tag est identique à la version (`1.0.0` ou `v1.0.0`). L'action **Build QGIS Plugin ZIP** attache l'archive à la release.

### Historique des versions

- **1.1.4** – Les bornes X restent appliquées dans chaque lot même si certaines valeurs X sont non numériques ; ces valeurs sont écartées de l'axe borné.
- **1.1.3** – Export CSV HORS_ZONE en UTF-8 sans BOM et séparateur virgule ; actualisation automatique de l'aperçu ; rattachement des lignes et polygones par intersection maximale avec départage par FID.
- **1.1.2** – Traduction anglaise complète des nouveaux libellés et messages de détection des bornes X.
- **1.1.1** – Détection des bornes X après filtre et sélection pour faciliter le calcul de `{duree}`.
- **1.1.0** – Rattachement spatial générique à une couche polygonale, graphique `HORS_ZONE`, export CSV de contrôle, constructeur d'expression, couleurs par série et aperçu du nom de fichier. 
- **1.0.0** – Première version.

## English

**Graphique Couche** (Layer Chart) is a QGIS plugin that turns the attribute table of **any vector layer** into a chart, with a preview, and exports it as an image. It is available from **Plugins → Layer Chart** and from a toolbar icon. It generalizes a drainage-monitoring script (charts per territory and for the whole department).

### Features

- Choose the **layer**, one or more **X fields** and the **Y field**. The first ticked X field in the list is the axis; the others form the series. Drag fields to reorder them.
- **Calculation** on Y: sum, mean, median, min, max, count, or no aggregation. With no Y field, features are counted.
- **Types**: bar, horizontal bar, stacked bar, line, area, scatter, pie, distribution histogram.
- **Title**, X and Y **axis labels**, **min/max scales** (empty = automatic), a dedicated button to detect the X range from filtered and selected data, per-series colours, legend, grid, value labels, label rotation, integer ticks.
- **QGIS expression** filter with expression builder and “selected features only”.
- Individually configurable series colours after preview.
- File name preview below the naming pattern.
- **Preview** in the dialog before exporting.
- **Export** to the folder of your choice as **PNG, JPEG, SVG, PDF or TIFF**, with adjustable resolution and size.
- **Batch mode**: one chart per value of a field, plus an optional global chart and a list of values to skip.
- **Optional spatial assignment**: assigns source features to any polygon layer using maximum intersection area for polygon sources, maximum intersection length for line sources, and the existing representative-point method for point sources (with CRS transformation if needed), without changing the source layer. Unmatched features are excluded from the territorial total and can produce a separate `HORS_ZONE` chart and audit CSV. For overlaps, the polygon with the lowest QGIS feature ID is selected.
- **Customizable file names** with tags: `{couche}` (layer) `{x}` `{y}` `{type}` `{agregation}` `{valeur}` (batch value) `{xmin}` `{xmax}` `{duree}` (X range length) `{date}` (YYYYMMDD) `{aamm}` (e.g. 2611). The extension is added automatically, unsafe characters are removed, duplicate names are made unique, and existing files are only overwritten after confirmation.
- Interface in French or English following the QGIS language; settings are remembered.

The plugin can now perform the spatial assignment itself; no pre-existing territory field is required. PDF atlas exports remain outside its scope.

### Installation

1. Download `qgis_plugin_graphique.zip` from the [Releases](https://github.com/shenri52/qgis_plugin_graphique/releases) page.
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the downloaded archive.

The plugin relies on **matplotlib**, bundled with QGIS on Windows and macOS. On Linux, install `python3-matplotlib` if it is missing.

### Version history

- **1.1.4** – X min/max bounds are applied independently in every batch, even when some X values are non-numeric; those values are excluded from the bounded axis.
- **1.1.3** – HORS_ZONE CSV uses UTF-8 without BOM and comma delimiter; preview refreshes when the selected value changes; line and polygon assignment uses maximum intersection measure with FID tie-break.
- **1.1.2** – Complete English translations for the X range detection controls and messages.
- **1.1.1** – Detect X min/max from filtered and selected numeric values for duration tags.
- **1.1.0** – Generic spatial assignment to a polygon layer, `HORS_ZONE` chart and optional CSV audit export. 
- **1.0.0** – Initial release.

## License

GPL-2.0. See [LICENSE](LICENSE).

## Project links

- Source code: <https://github.com/shenri52/qgis_plugin_graphique>
- Issue tracker: <https://github.com/shenri52/qgis_plugin_graphique/issues>
