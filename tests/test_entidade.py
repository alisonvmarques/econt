import sqlite3

import pytest
from PySide6.QtGui import QColor, QImage

from baliza.dados.banco import BaseDeDados
from baliza.dados.entidade import Entidade, EntidadeInvalida, obter_entidade, salvar_entidade
from baliza.interface.area_principal import LARGURA_NOME, AreaPrincipal, em_duas_linhas
from baliza.interface.entidade import LogoInvalido, PaginaEntidade, TelaDadosEntidade, preparar_logo
from baliza.interface.impressao import html_chave_recuperacao, salvar_pdf
from baliza.interface.janela_principal import JanelaPrincipal

SENHA = "fundo2026saude"
CNPJ = "11.222.333/0001-81"


def _logo(tmp_path, lado=600):
    caminho = tmp_path / "logo.png"
    imagem = QImage(lado, lado // 2, QImage.Format.Format_RGB32)
    imagem.fill(QColor("#2E6A6E"))
    imagem.save(str(caminho))
    return caminho


def _base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]


def test_uma_unica_entidade(tmp_path):
    base = _base(tmp_path)
    salvar_entidade(base.conexao, Entidade("Fundo de Saúde Exemplo", CNPJ))
    salvar_entidade(base.conexao, Entidade("Fundo Renomeado", CNPJ))
    assert base.conexao.execute("SELECT count(*) FROM entidade").fetchone()[0] == 1
    assert obter_entidade(base.conexao).razao_social == "Fundo Renomeado"
    with pytest.raises(sqlite3.IntegrityError):
        base.conexao.execute(
            "INSERT INTO entidade VALUES (2, 'Outra', '11222333000181', NULL, 'x', 'x')"
        )


def test_cnpj_invalido_nao_e_salvo(tmp_path):
    base = _base(tmp_path)
    with pytest.raises(EntidadeInvalida, match="CNPJ inválido"):
        salvar_entidade(base.conexao, Entidade("Fundo", "11.222.333/0001-80"))


def test_primeiro_uso_pede_a_entidade_antes_do_resto(aplicacao, tmp_path):
    caminho = tmp_path / "dados.baliza"
    janela = JanelaPrincipal(caminho)
    tela = janela.tela_atual()
    tela.senha.definir(SENHA)
    tela.confirma.definir(SENHA)
    tela.criar.click()
    janela.tela_atual().guardei.setChecked(True)
    janela.tela_atual().botao_continuar.click()

    tela = janela.tela_atual()
    assert isinstance(tela, TelaDadosEntidade)
    tela.formulario.razao_social.definir("Fundo de Saúde Exemplo")
    tela.formulario.cnpj.definir("11.222.333/0001-80")
    tela.salvar.click()
    assert tela.formulario.cnpj.tem_erro()
    assert isinstance(janela.tela_atual(), TelaDadosEntidade)

    tela.formulario.cnpj.definir(CNPJ)
    assert tela.formulario.carregar_logo(_logo(tmp_path))
    tela.salvar.click()
    assert isinstance(janela.tela_atual(), AreaPrincipal)
    assert janela.area.navegacao.nome_entidade.text().replace("\n", " ") == "Fundo de Saúde Exemplo"
    assert not janela.area.navegacao.logo.pixmap().isNull()
    janela.close()

    aberta = BaseDeDados.abrir(caminho, senha=SENHA)
    entidade = obter_entidade(aberta.conexao)
    assert entidade.cnpj == "11222333000181" and entidade.logo


def test_entidade_editada_na_area_entidade(aplicacao, tmp_path):
    base = _base(tmp_path)
    salvar_entidade(base.conexao, Entidade("Fundo de Saúde Exemplo", CNPJ))
    area = AreaPrincipal(base)
    area.navegacao.botoes["entidade"].click()
    pagina = area.paginas.currentWidget()
    assert isinstance(pagina, PaginaEntidade)
    pagina.formulario.razao_social.definir("Fundo de Saúde Exemplo II")
    pagina.salvar.click()
    assert obter_entidade(base.conexao).razao_social == "Fundo de Saúde Exemplo II"
    assert area.navegacao.nome_entidade.toolTip() == "Fundo de Saúde Exemplo II"


def test_sem_logo_o_espaco_fica_vazio(aplicacao, tmp_path):
    base = _base(tmp_path)
    salvar_entidade(base.conexao, Entidade("Fundo", CNPJ))
    area = AreaPrincipal(base)
    assert area.navegacao.logo.pixmap().isNull()
    assert area.navegacao.logo.width() == 32


def test_logo_reduzido_e_arquivo_grande_recusado(aplicacao, tmp_path):
    dados = preparar_logo(_logo(tmp_path, 900))
    imagem = QImage.fromData(dados)
    assert max(imagem.width(), imagem.height()) == 256
    grande = tmp_path / "grande.png"
    grande.write_bytes(b"0" * (1024 * 1024 + 1))
    with pytest.raises(LogoInvalido, match="até 1 MB"):
        preparar_logo(grande)


def test_logo_no_cabecalho_da_impressao(aplicacao, tmp_path):
    from datetime import datetime

    logo = preparar_logo(_logo(tmp_path))
    html = html_chave_recuperacao(
        "ABCD-EFGH-JKLM-NPQR-STUV-WXYZ", datetime.now(), "Fundo", CNPJ, True
    )
    assert 'src="baliza://logo"' in html
    pdf_com = tmp_path / "com.pdf"
    pdf_sem = tmp_path / "sem.pdf"
    salvar_pdf(html, str(pdf_com), logo)
    salvar_pdf(html_chave_recuperacao("ABCD", datetime.now(), "Fundo", CNPJ), str(pdf_sem))
    assert pdf_com.stat().st_size > pdf_sem.stat().st_size


def test_nome_longo_em_duas_linhas_com_reticencias(aplicacao, tmp_path):
    base = _base(tmp_path)
    nome = "Fundo Municipal de Saúde e Assistência Social Exemplo"
    salvar_entidade(base.conexao, Entidade(nome, CNPJ))
    area = AreaPrincipal(base)
    rotulo = area.navegacao.nome_entidade
    linhas = rotulo.text().split("\n")
    assert len(linhas) == 2 and linhas[1].endswith("…")
    assert all(rotulo.fontMetrics().horizontalAdvance(ln) <= LARGURA_NOME for ln in linhas)
    assert rotulo.toolTip() == nome


def test_nome_curto_fica_inteiro():
    from PySide6.QtGui import QFont, QFontMetrics

    medidas = QFontMetrics(QFont("Inter", 11))
    assert em_duas_linhas("Fundo", medidas, LARGURA_NOME) == "Fundo"
    assert "…" not in em_duas_linhas("Fundo de Saúde Exemplo", medidas, LARGURA_NOME)
