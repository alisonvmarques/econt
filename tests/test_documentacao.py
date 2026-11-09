"""Documentação (#53, #54): README, guias de uso e o site gerado a partir de docs/."""

import re
import unicodedata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
GUIAS = [
    "index.md",
    "instalacao.md",
    "primeiros-passos.md",
    "inicio.md",
    "consulta.md",
    "fornecedores.md",
    "entidade.md",
    "configuracoes.md",
    "perguntas-frequentes.md",
]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")


def _paginas() -> list[Path]:
    return [RAIZ / "README.md", RAIZ / "CONTRIBUTING.md", *sorted(DOCS.glob("*.md"))]


def _ancora(titulo: str) -> str:
    """Âncora de um título, igual no GitHub e no site para títulos sem acento."""
    texto = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^\w\s-]", "", texto).strip().lower()
    return re.sub(r"\s+", "-", texto)


def _titulos(pagina: Path) -> dict[str, str]:
    linhas = pagina.read_text(encoding="utf-8").splitlines()
    return {_ancora(ln.lstrip("#")): ln for ln in linhas if ln.startswith("#")}


def test_um_guia_para_cada_area_e_primeiros_passos():
    for guia in GUIAS:
        assert (DOCS / guia).is_file(), guia


@pytest.mark.parametrize("pagina", _paginas(), ids=lambda p: p.name)
def test_links_e_imagens_apontam_para_o_que_existe(pagina):
    for alvo in LINK.findall(pagina.read_text(encoding="utf-8")):
        if alvo.startswith(("http://", "https://")):
            continue
        caminho, _, ancora = alvo.partition("#")
        destino = (pagina.parent / caminho).resolve() if caminho else pagina
        assert destino.exists(), f"{pagina.name}: {alvo}"
        if ancora:
            titulos = _titulos(destino)
            assert ancora in titulos, f"{pagina.name}: âncora {alvo}"
            # Com acento, a âncora muda entre o GitHub e o site: só títulos sem acento.
            assert titulos[ancora].isascii(), f"{pagina.name}: título com acento em {alvo}"


def test_toda_captura_e_usada_e_toda_pagina_esta_no_site():
    usadas = set()
    for pagina in _paginas():
        usadas |= {Path(a).name for a in LINK.findall(pagina.read_text(encoding="utf-8"))}
    for imagem in (DOCS / "imagens").glob("*.png"):
        assert imagem.name in usadas, f"captura sem uso: {imagem.name}"
    site = (RAIZ / "mkdocs.yml").read_text(encoding="utf-8")
    assert "docs_dir: docs" in site
    for pagina in DOCS.glob("*.md"):
        assert f": {pagina.name}" in site, f"fora do site: {pagina.name}"


def test_readme_diz_o_que_e_como_instalar_licenca_e_contribuicao():
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    for secao in ("## Para quem é", "## O que o Baliza faz", "## Instalação", "## Licença"):
        assert secao in readme
    for sistema in ("Windows", "Linux", "macOS"):
        assert sistema in readme
    assert "CONTRIBUTING.md" in readme and (RAIZ / "LICENSE").is_file()
    assert "dados fictícios" in readme


def test_capturas_so_com_dados_ficticios():
    """O script das capturas cria os próprios dados numa pasta temporária."""
    script = (RAIZ / "scripts" / "capturas.py").read_text(encoding="utf-8")
    assert "TemporaryDirectory" in script and "BALIZA_ARQUIVO" in script
    assert "caminho_padrao" not in script
