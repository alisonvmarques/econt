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
    from econt import __version__

    empacotar = _script()
    assert empacotar.versao() == __version__
    assert empacotar.sistema() in {"windows", "macos", "linux"}
    assert empacotar.ICONE_SVG.is_file()


def test_instalador_windows_em_portugues_e_sem_administrador():
    iss = (RAIZ / "empacotamento" / "windows" / "econt.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss
    assert "BrazilianPortuguese.isl" in iss
    assert "OutputBaseFilename=ECont-{#Versao}-Windows-instalador" in iss


def test_appimage_aponta_para_o_programa():
    apprun = (RAIZ / "empacotamento" / "linux" / "AppRun").read_text(encoding="utf-8")
    desktop = (RAIZ / "empacotamento" / "linux" / "econt.desktop").read_text(encoding="utf-8")
    assert "usr/lib/econt/ECont" in apprun
    assert "Icon=econt" in desktop and "Name=ECont" in desktop


def test_workflow_gera_e_confere_nos_tres_sistemas():
    workflow = (RAIZ / ".github" / "workflows" / "instaladores.yml").read_text(encoding="utf-8")
    for sistema in ("ubuntu-22.04", "windows-latest", "macos-latest"):
        assert sistema in workflow
    assert "types: [published]" in workflow and "workflow_dispatch" in workflow
    assert "python scripts/empacotar.py verificar" in workflow


def test_pacote_deb_instala_comando_atalho_e_icone(tmp_path, monkeypatch):
    """Monta o .deb com um programa de mentira e confere o que ele instala."""
    import shutil
    import subprocess

    import pytest

    if shutil.which("dpkg-deb") is None:
        pytest.skip("dpkg-deb só existe no Debian e no Ubuntu")
    empacotar = _script()
    dist, obra = tmp_path / "dist", tmp_path / "obra"
    (dist / "ECont").mkdir(parents=True)
    (dist / "ECont" / "ECont").write_text("#!/bin/sh\n", encoding="utf-8")
    (dist / "ECont" / "ECont").chmod(0o755)
    png = tmp_path / "econt.png"
    png.write_bytes(b"png")
    monkeypatch.setattr(empacotar, "DIST", dist)
    monkeypatch.setattr(empacotar, "OBRA", obra)

    deb = empacotar.pacote_deb({"png": png})

    assert deb.name == f"econt_{empacotar.versao()}_amd64.deb"
    conteudo = subprocess.run(["dpkg-deb", "-c", deb], capture_output=True, text=True).stdout
    for caminho in (
        "./opt/econt/ECont",
        "./usr/bin/econt -> ../../opt/econt/ECont",
        "./usr/share/applications/econt.desktop",
        "./usr/share/icons/hicolor/256x256/apps/econt.png",
        "./usr/share/icons/hicolor/scalable/apps/econt.svg",
    ):
        assert caminho in conteudo
    campos = subprocess.run(["dpkg-deb", "-f", deb], capture_output=True, text=True).stdout
    assert "Package: econt" in campos and "Depends: libegl1" in campos
    extraido = tmp_path / "x"
    subprocess.run(["dpkg-deb", "-x", deb, extraido], check=True)
    atalho = (extraido / "usr/share/applications/econt.desktop").read_text(encoding="utf-8")
    assert "Exec=econt" in atalho and "StartupWMClass=ECont" in atalho


def test_workflow_instala_o_deb_antes_de_conferir():
    workflow = (RAIZ / ".github" / "workflows" / "instaladores.yml").read_text(encoding="utf-8")
    assert "sudo apt-get install -y ./dist/econt_*_amd64.deb" in workflow
    assert "dist/econt_*.deb" in workflow
    assert workflow.index("apt-get install -y ./dist") < workflow.index("empacotar.py verificar")


def test_versao_publicada_anexa_instaladores_e_publica_o_site():
    workflow = (RAIZ / ".github" / "workflows" / "instaladores.yml").read_text(encoding="utf-8")
    assert "release:\n    types: [published]" in workflow
    assert 'gh release upload "${GITHUB_REF_NAME}"' in workflow
    assert "secrets.APT_CHAVE_PRIVADA" in workflow
    assert "actions/deploy-pages" in workflow
    assert "mkdocs build --strict" in workflow


def test_repositorio_apt_assinado(tmp_path):
    """Monta o repositório com uma chave de teste e confere a assinatura e os índices."""
    import os
    import shutil
    import subprocess

    import pytest

    if not (shutil.which("apt-ftparchive") and shutil.which("gpg")):
        pytest.skip("apt-ftparchive e gpg só existem no Debian e no Ubuntu")
    ambiente = {**os.environ, "GNUPGHOME": str(tmp_path / "gnupg")}
    (tmp_path / "gnupg").mkdir(mode=0o700)
    subprocess.run(
        ["gpg", "--batch", "--passphrase", "", "--quick-gen-key", "Teste", "ed25519", "sign"],
        env=ambiente,
        check=True,
        capture_output=True,
    )
    origem = tmp_path / "dist"
    origem.mkdir()
    (origem / "econt_1.0.0_amd64.deb").write_bytes(b"!<arch>\n")
    destino = tmp_path / "site" / "apt"
    subprocess.run(
        ["bash", RAIZ / "scripts" / "repositorio_apt.sh", origem, destino],
        env=ambiente,
        check=True,
        capture_output=True,
    )
    for arquivo in ("Packages", "Packages.gz", "Release", "InRelease", "Release.gpg"):
        assert (destino / arquivo).is_file(), arquivo
    release = (destino / "Release").read_text(encoding="utf-8")
    assert " Packages\n" in release and " Release\n" not in release
    conferido = subprocess.run(
        ["gpg", "--verify", destino / "InRelease"], env=ambiente, capture_output=True
    )
    assert conferido.returncode == 0
