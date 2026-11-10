from datetime import datetime

from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta, registrar_pedido
from econt.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from econt.dados.marcacoes import itens_do_fornecedor, marcar_todas
from econt.dados.painel import resumir

AGORA = datetime(2026, 11, 8, 10, 15)


def test_resumo_conta_o_que_vale(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.econt", "fundo2026saude")[0]
    c = base.conexao
    assert resumir(c, AGORA).fornecedores_ativos == 0
    pix = cadastrar_conta(c, DadosConta("Conta Pix", "001", "1234-5", "66666-2"))
    registrar_pedido(c, pix, "pix", 3_000_000, AGORA, AGORA)
    a = cadastrar_fornecedor(c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora"))
    salvar_conta_fornecedor(c, a, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_chave_pix(c, a, "email", "financeiro@exemplo.com.br")
    marcar_todas(c, itens_do_fornecedor(c, a)[0])
    b = cadastrar_fornecedor(c, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    salvar_chave_pix(c, b, "cpf", "529.982.247-25")
    definir_fornecedor_ativo(c, b, False)
    resumo = resumir(c, AGORA)
    assert resumo.fornecedores_ativos == 1
    assert resumo.contas_e_chaves == 2
    assert resumo.contas_entidade == 1
    assert resumo.sem_cadastro == 1
    assert resumo.limites_em_liberacao == [
        "O limite Pix da Conta Pix muda para R$ 30.000,00 em 09/11/2026 às 10:15."
    ]
