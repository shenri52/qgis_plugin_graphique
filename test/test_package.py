# -*- coding: utf-8 -*-
"""Contrôles du paquet : métadonnées, traductions, règles de sécurité."""
import ast
import configparser
import os
import re

from qgis_plugin_graphique import core, i18n

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qgis_plugin_graphique")
SOURCES = sorted(f for f in os.listdir(PLUGIN_DIR) if f.endswith(".py"))


def parse(name):
    with open(os.path.join(PLUGIN_DIR, name), encoding="utf-8") as handle:
        return ast.parse(handle.read())


def test_metadata_is_complete():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(os.path.join(PLUGIN_DIR, "metadata.txt"), encoding="utf-8")
    general = parser["general"]
    for key in ("name", "qgisMinimumVersion", "description", "about", "version", "author", "email",
                "tracker", "repository", "homepage", "tags", "icon", "changelog"):
        assert general.get(key), key
    assert re.fullmatch(r"\d+\.\d+\.\d+", general["version"])
    assert general["tracker"].startswith("https://") and general["repository"].startswith("https://")
    assert os.path.isfile(os.path.join(PLUGIN_DIR, general["icon"]))
    assert os.path.isfile(os.path.join(PLUGIN_DIR, "LICENSE"))
    assert general["version"] in general["changelog"]


def test_class_factory_exists():
    names = {n.name for n in parse("__init__.py").body if isinstance(n, ast.FunctionDef)}
    assert "classFactory" in names


def tr_literals():
    found = set()
    for name in ("dialog.py", "plugin.py", "data.py", "render.py"):
        for node in ast.walk(parse(name)):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "tr"
                    and node.args and isinstance(node.args[0], ast.Constant)):
                found.add(node.args[0].value)
    return found


def test_every_translated_text_has_an_english_version():
    missing = sorted(t for t in tr_literals() if t not in i18n.EN)
    assert not missing, missing


def test_no_unused_translations():
    used = tr_literals()
    # les libellés de listes déclarés dans dialog.py passent par tr(label) dans _combo()
    for node in ast.walk(parse("dialog.py")):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.add(node.value)
    unused = sorted(k for k in i18n.EN if k not in used)
    assert not unused, unused


def test_placeholders_are_documented_in_the_dialog():
    help_text = next(k for k in i18n.EN if k.startswith("Balises"))
    for tag in core.PLACEHOLDERS:
        assert "{" + tag + "}" in help_text, tag


def test_presets_use_known_placeholders():
    for preset in i18n.PRESET_NAMES:
        assert core.unknown_placeholders(preset) == []


FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_ATTRS = {"Popen", "check_output", "check_call", "loads", "load"}
FORBIDDEN_OS = {"system", "popen"}
FORBIDDEN_IMPORTS = {"subprocess", "pickle", "marshal", "shelve", "socket", "urllib", "requests", "ftplib"}


def test_no_dangerous_constructs():
    for name in SOURCES:
        for node in ast.walk(parse(name)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for module in modules:
                    assert module.split(".")[0] not in FORBIDDEN_IMPORTS, (name, module)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in FORBIDDEN_NAMES, (name, node.func.id)
                if isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in FORBIDDEN_ATTRS, (name, node.func.attr)
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        assert node.func.attr not in FORBIDDEN_OS, (name, node.func.attr)
            if isinstance(node, ast.ExceptHandler):
                assert node.type is not None, (name, "except: nu")
                assert not (len(node.body) == 1 and isinstance(node.body[0], (ast.Pass, ast.Continue))), (
                    name, "except silencieux")
            assert not isinstance(node, ast.Assert), (name, "assert")
