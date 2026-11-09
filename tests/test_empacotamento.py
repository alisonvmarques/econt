"""Os arquivos de empacotamento conferem com o que o programa espera (RNF10)."""

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _script():
    especificacao = importlib.util.spec_from_file_location(
        "empacotar", RAIZ / "scripts" / "empacotar.py"
    )
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_nomes_dos_instaladores_levam_a_versao():
    from baliza import __version__

    empacotar = _script()
    assert empacotar.versao() == __version__
    assert empacotar.sistema() in {"windows", "macos", "linux"}
    assert empacotar.ICONE_SVG.is_file()


def test_instalador_windows_em_portugues_e_sem_administrador():
    iss = (RAIZ / "empacotamento" / "windows" / "baliza.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss
    assert "BrazilianPortuguese.isl" in iss
    assert "OutputBaseFilename=Baliza-{#Versao}-Windows-instalador" in iss


def test_appimage_aponta_para_o_programa():
    apprun = (RAIZ / "empacotamento" / "linux" / "AppRun").read_text(encoding="utf-8")
    desktop = (RAIZ / "empacotamento" / "linux" / "baliza.desktop").read_text(encoding="utf-8")
    assert "usr/lib/baliza/Baliza" in apprun
    assert "Icon=baliza" in desktop and "Name=Baliza" in desktop


def test_workflow_gera_e_confere_nos_tres_sistemas():
    workflow = (RAIZ / ".github" / "workflows" / "instaladores.yml").read_text(encoding="utf-8")
    for sistema in ("ubuntu-22.04", "windows-latest", "macos-latest"):
        assert sistema in workflow
    assert 'tags: ["v*"]' in workflow
    assert "python scripts/empacotar.py verificar" in workflow
