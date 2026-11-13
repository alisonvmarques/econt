"""Gera as capturas de tela da documentação, só com dados fictícios.

    QT_QPA_PLATFORM=offscreen python scripts/capturas.py

As imagens vão para docs/imagens. Os dados são criados numa pasta temporária: nada do
arquivo de dados de verdade é lido ou alterado.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from econt.app import criar_aplicacao
from econt.dados.atividades import (
    DadosAtividade,
    arquivar_atividade,
    criar_atividade,
    mover_atividade,
)
from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta, registrar_pedido
from econt.dados.entidade import Entidade, salvar_entidade
from econt.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from econt.dados.marcacoes import definir_marcacao, itens_do_fornecedor, marcar_todas
from econt.dominio.documentos import cnpj_valido, formatar_cnpj

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "imagens"
SENHA = "exemplo2026econt"


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
    atividades_de_exemplo(c, ids[0], ids[1])
    base.salvar()
    return base


def atividades_de_exemplo(c, distribuidora: int, laboratorio: int) -> None:
    """Um quadro com atividades inventadas, com prazos em volta de hoje."""
    hoje = date.today()
    a_fazer, em_andamento, concluido = 1, 2, 3
    exemplos = [
        (a_fazer, "Conferir notas fiscais de outubro", -2, distribuidora, ""),
        (a_fazer, "Pagar conta de energia da sede", 0, None, "Vence às 16h no banco."),
        (a_fazer, "Atualizar certidões dos fornecedores", 6, None, ""),
        (a_fazer, "Separar comprovantes para a prestação de contas", None, None, ""),
        (em_andamento, "Pedir aumento do limite Pix da Conta Pix", 3, None, ""),
        (em_andamento, "Cadastrar favorecido do laboratório", 1, laboratorio, ""),
        (concluido, "Fechar o mês de setembro", -10, None, ""),
        (concluido, "Renovar contrato de limpeza", -4, None, ""),
    ]
    for coluna, titulo, dias, fornecedor, descricao in exemplos:
        prazo = hoje + timedelta(days=dias) if dias is not None else None
        criar_atividade(c, coluna, DadosAtividade(titulo, descricao, prazo, fornecedor))
    antiga = criar_atividade(c, a_fazer, DadosAtividade("Reunião com o contador"))
    mover_atividade(c, antiga, concluido, 1)
    arquivar_atividade(c, antiga)


def capturar(janela, nome: str) -> None:
    for _ in range(3):
        QCoreApplication.processEvents()
    janela.grab().save(str(DESTINO / f"{nome}.png"))
    print(f"docs/imagens/{nome}.png")


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    DESTINO.mkdir(parents=True, exist_ok=True)
    aplicacao = criar_aplicacao([sys.argv[0]])
    from econt.interface.janela_principal import JanelaPrincipal

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "dados.econt"
        os.environ["ECONT_ARQUIVO"] = str(caminho)
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

        area.ir_para("atividades")
        atividades = area.indice["atividades"]
        atividades.focar(atividades.colunas[0].cartoes[0].id)
        capturar(janela, "atividades")
        dialogo = atividades.criar_dialogo_atividade(0, atividades.colunas[1].cartoes[1].id)
        dialogo.show()
        capturar(dialogo, "atividade-editar")
        dialogo.close()

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
