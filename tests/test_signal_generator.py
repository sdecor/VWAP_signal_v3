# tests/test_signal_generator.py

import os
import json
import sys
import textwrap
import importlib
import types
import pathlib

import pytest

# Assure que la racine projet est dans le PYTHONPATH (au cas où)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import signal_generator  # module à tester


def write_rule(tmpdir, filename: str, content: str) -> str:
    """Crée un fichier de règle python et renvoie son chemin complet."""
    path = os.path.join(tmpdir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
    return path


def test_apply_with_config_injection(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # Cette règle exige un paramètre config et écrit un fichier preuve
    marker_file = tmp_path / "with_config_marker.json"
    rule_code = f"""
    def apply(config, *args, **kwargs):
        assert isinstance(config, dict)
        # produire une preuve
        import json
        with open(r"{marker_file}", "w", encoding="utf-8") as f:
            json.dump({{"ok": True, "value": config.get("model", {{}}).get("path", "")}}, f)
    """
    write_rule(str(rules_dir), "rule_with_config.py", rule_code)

    fake_config = {"model": {"path": "E:/fake/model.json"}}
    signal_generator.run_all_signals(str(rules_dir), config=fake_config)

    assert marker_file.exists(), "La règle avec config n'a pas été exécutée."
    data = json.loads(marker_file.read_text(encoding="utf-8"))
    assert data["ok"] is True
    assert data["value"] == "E:/fake/model.json"


def test_apply_without_config_still_runs(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    marker_file = tmp_path / "no_config_marker.txt"
    rule_code = f"""
    def apply(*args, **kwargs):
        # pas de param 'config' ici
        with open(r"{marker_file}", "w", encoding="utf-8") as f:
            f.write("ran")
    """
    write_rule(str(rules_dir), "rule_no_config.py", rule_code)

    # Même si on passe une config, elle ne sera pas injectée à cette règle
    fake_config = {"anything": 123}
    signal_generator.run_all_signals(str(rules_dir), config=fake_config)

    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8") == "ran"


def test_module_without_apply_is_ignored(tmp_path, capsys):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    # module sans apply()
    write_rule(str(rules_dir), "no_apply_module.py", "X = 1\nY = 2\n")

    signal_generator.run_all_signals(str(rules_dir), config={})
    out = capsys.readouterr().out

    assert "ne contient pas de fonction 'apply'" in out


def test_exception_in_one_rule_does_not_stop_others(tmp_path, capsys):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    good_marker = tmp_path / "good_rule.txt"

    bad_rule = """
    def apply(*args, **kwargs):
        raise RuntimeError("Boom!")
    """
    good_rule = f"""
    def apply(*args, **kwargs):
        with open(r"{good_marker}", "w", encoding="utf-8") as f:
            f.write("ok")
    """
    write_rule(str(rules_dir), "bad_rule.py", bad_rule)
    write_rule(str(rules_dir), "good_rule.py", good_rule)

    signal_generator.run_all_signals(str(rules_dir), config={})
    out = capsys.readouterr().out

    # On a loggé l'erreur mais l'autre règle a bien tourné
    assert "Erreur durant l'exécution de bad_rule.py" in out
    assert good_marker.exists()
    assert good_marker.read_text(encoding="utf-8") == "ok"


def test_nonexistent_rules_directory_is_graceful(tmp_path, capsys):
    # ne crée pas le répertoire
    missing_dir = tmp_path / "no_rules_here"

    signal_generator.run_all_signals(str(missing_dir), config={})
    out = capsys.readouterr().out
    assert "Répertoire de règles introuvable" in out


def test_load_config_failure_allows_rules_without_config(tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()

    marker_file = tmp_path / "ran.txt"
    rule_code = f"""
    def apply(*args, **kwargs):
        # Ne demande pas 'config', doit s'exécuter même si load_config échoue
        with open(r"{marker_file}", "w", encoding="utf-8") as f:
            f.write("ok")
    """
    write_rule(str(rules_dir), "no_config_rule.py", rule_code)

    # On force run_all_signals à ne PAS recevoir config, et à échouer sur load_config()
    def fake_load_config():
        raise RuntimeError("config load failed")

    monkeypatch.setattr(signal_generator, "load_config", fake_load_config)

    # Appel sans config -> le loader échoue, mais les règles sans config doivent encore s'exécuter
    signal_generator.run_all_signals(str(rules_dir))
    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8") == "ok"
