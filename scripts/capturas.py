"""Gera as capturas de tela da documentação, só com dados fictícios.

    QT_QPA_PLATFORM=offscreen python scripts/capturas.py

As imagens vão para docs/imagens. Os dados são criados numa pasta temporária: nada do
arquivo de dados de verdade é lido ou alterado.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from baliza.app import criar_aplicacao
from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import DadosConta, cadastrar_conta, registrar_pedido
from baliza.dados.entidade import Entidade, salvar_entidade
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from baliza.dados.marcacoes import definir_marcacao, itens_do_fornecedor, marcar_todas
from baliza.dominio.documentos import cnpj_valido, formatar_cnpj

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "imagens"
SENHA = "exemplo2026baliza"


def cnpj(base: str) -> str:
    """CNPJ fictício com os dígitos verificadores certos, a partir dos 12 primeiros."""
    for dv in range(100):
        numero = f"{base}{dv:02d}"
        if cnpj_valido(numero):
            return formatar_cnpj(numero)
    raise ValueError(base)


def dados_de_exemplo(caminho: Path) -> BaseDeDados:
    """Uma entidade fictícia, três contas e alguns fornecedores, todos inventados."""
    base = BaseDeDados.criar(caminho, SENHA)[0]
    base.definir_configuracao("chave_de_recuperacao_guardada", "sim")
    c = base.conexao
    salvar_entidade(c, Entidade("Fundo Municipal de Saúde Exemplo", cnpj("112223330001")))
    cadastrar_conta(c, DadosConta("Conta Movimento", "001", "1234-5", "55555-0"))
    cadastrar_conta(c, DadosConta("Conta Saúde", "104", "0456", "77777-1"))
    pix = cadastrar_conta(c, DadosConta("Conta Pix", "341", "0789", "66666-2"))
    agora = datetime.now().replace(second=0, microsecond=0)
    registrar_pedido(c, pix, "pix", 3_000_000, agora - timedelta(hours=2), agora)

    fornecedores = [
        ("123456780001", "Distribuidora Exemplo de Materiais Ltda", "Exemplo Materiais"),
        ("234567890001", "Laboratório Modelo de Análises Ltda", "Lab Modelo"),
        ("345678900001", "Papelaria Fictícia do Centro Ltda", "Papelaria Centro"),
        ("456789010001", "Serviços de Limpeza Imaginária Ltda", ""),
        ("567890120001", "Transportes Ilustrativos Ltda", ""),
    ]
    ids = []
    for numero, (raiz, razao, fantasia) in enumerate(fornecedores):
        f = cadastrar_fornecedor(
            c,
            DadosFornecedor(
                "pj",
                cnpj(raiz),
                razao,
                nome_fantasia=fantasia,
                telefone="(11) 3333-0000",
                email="financeiro@exemplo.com.br",
            ),
        )
        ids.append(f)
        salvar_conta_fornecedor(c, f, DadosContaFornecedor("001", "1234-5", f"9876{numero}-4"))
        if numero == 0:
            salvar_conta_fornecedor(c, f, DadosContaFornecedor("237", "0101", "22222-3"))
            salvar_chave_pix(c, f, "email", "financeiro@exemplo.com.br")
        for item in itens_do_fornecedor(c, f):
            marcar_todas(c, item)
    # Uma conta da distribuidora ainda sem cadastro na Conta Pix: aparece como pendente.
    segunda = itens_do_fornecedor(c, ids[0])[1]
    definir_marcacao(c, segunda, pix, False)
    # Um fornecedor novo, ainda sem cadastro em nenhuma conta da entidade.
    novo = cadastrar_fornecedor(
        c, DadosFornecedor("pj", cnpj("678901230001"), "Gráfica Hipotética Ltda")
    )
    salvar_chave_pix(c, novo, "cnpj", cnpj("678901230001"))
    base.salvar()
    return base


def capturar(janela, nome: str) -> None:
    for _ in range(3):
        QCoreApplication.processEvents()
    janela.grab().save(str(DESTINO / f"{nome}.png"))
    print(f"docs/imagens/{nome}.png")


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    DESTINO.mkdir(parents=True, exist_ok=True)
    aplicacao = criar_aplicacao([sys.argv[0]])
    from baliza.interface.janela_principal import JanelaPrincipal

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "dados.baliza"
        os.environ["BALIZA_ARQUIVO"] = str(caminho)
        base = dados_de_exemplo(caminho)
        base.fechar()

        janela = JanelaPrincipal(caminho)
        janela.show()
        capturar(janela, "entrada")
        janela._acesso_liberado(BaseDeDados.abrir(caminho, senha=SENHA))
        area = janela.area

        area.ir_para("inicio")
        capturar(janela, "inicio")

        area.ir_para("consulta")
        consulta = area.indice["consulta"]
        consulta.busca.setText("exemplo")
        capturar(janela, "consulta-busca")
        consulta._abrir_primeiro()
        capturar(janela, "consulta-resultado")

        area.ir_para("fornecedores")
        fornecedores = area.indice["fornecedores"]
        capturar(janela, "fornecedores")
        fornecedores.abrir_ficha(1)  # a distribuidora, a primeira cadastrada
        ficha = fornecedores.currentWidget()
        ficha.abas.setCurrentIndex(1)
        capturar(janela, "fornecedor-contas")
        ficha.abas.setCurrentIndex(2)
        capturar(janela, "fornecedor-cadastros")

        area.ir_para("entidade")
        entidade = area.indice["entidade"]
        entidade.abas.setCurrentIndex(1)
        capturar(janela, "entidade-contas")

        area.ir_para("configuracoes")
        capturar(janela, "configuracoes")

        janela.base.salvar()
        janela.base.conexao.close()
        janela.base = None
        janela.close()
    aplicacao.processEvents()
    return 0


if __name__ == "__main__":
    sys.exit(main())
