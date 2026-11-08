import pytest

from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import DadosConta, cadastrar_conta
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    listar_chaves,
    listar_contas_fornecedor,
    listar_fornecedores,
    obter_fornecedor,
    salvar_conta_fornecedor,
)
from baliza.interface import fornecedores as telas
from baliza.interface.area_principal import AreaPrincipal
from baliza.interface.fornecedores import PaginaFornecedores

SENHA = "fundo2026saude"
MATERIAIS = DadosFornecedor(
    "pj",
    "11.222.333/0001-81",
    "Distribuidora Exemplo de Materiais Ltda",
    "Exemplo Materiais",
    "(81) 3000-0000",
    "contato@exemplo.com.br",
    "Rua Fictícia, 100 · Recife/PE",
)
MARIA = DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo da Silva")


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]


def _sem_janela(dialogo):
    """Confirma o diálogo sem abrir janela modal."""
    dialogo.exec = lambda: (dialogo.confirmar.click(), dialogo.result())[1]
    return dialogo


def test_area_fornecedores_mostra_a_lista(aplicacao, base):
    area = AreaPrincipal(base)
    area.navegacao.botoes["fornecedores"].click()
    pagina = area.paginas.currentWidget()
    assert isinstance(pagina, PaginaFornecedores)
    assert "Nenhum fornecedor cadastrado" in pagina.lista.vazia.text()


def test_novo_fornecedor_pelo_formulario(aplicacao, base):
    pagina = PaginaFornecedores(base)
    pagina.lista.novo.click()
    form = pagina.formulario
    assert pagina.currentWidget() is form
    form.documento.definir("11222333000181")
    form.razao_social.definir("Distribuidora Exemplo de Materiais Ltda")
    form.email.definir("contato@exemplo.com.br")
    form.salvar.click()
    assert pagina.currentWidget() is pagina.ficha
    assert pagina.ficha.titulo.text() == "Distribuidora Exemplo de Materiais Ltda"
    assert pagina.ficha.documento.text() == "CNPJ 11.222.333/0001-81"
    assert [pagina.ficha.abas.tabText(i) for i in range(3)] == [
        "Dados",
        "Contas e Pix",
        "Cadastros",
    ]
    pagina.ficha.voltar.click()
    assert pagina.lista.tabela.rowCount() == 1


def test_formulario_mostra_os_erros(aplicacao, base):
    cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.lista.novo.click()
    form = pagina.formulario
    form.documento.definir("11.222.333/0001-81")
    form.email.definir("contato@")
    form.salvar.click()
    assert "já é de Distribuidora" in form.documento.linha_ajuda.text()
    assert form.razao_social.tem_erro()
    assert form.email.tem_erro()
    assert len(listar_fornecedores(base.conexao)) == 1


def test_pessoa_fisica_troca_rotulos(aplicacao, base):
    pagina = PaginaFornecedores(base)
    pagina.lista.novo.click()
    form = pagina.formulario
    form.tipo.definir("pf")
    assert form.documento.rotulo.text() == "CPF"
    assert form.razao_social.rotulo.text() == "Nome"
    assert not form.nome_fantasia.isVisibleTo(form)
    form.documento.definir("529.982.247-24")
    form.razao_social.definir("Maria Exemplo da Silva")
    form.salvar.click()
    assert "CPF inválido" in form.documento.linha_ajuda.text()


def test_editar_pela_ficha(aplicacao, base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(fornecedor_id)
    pagina.ficha.editar.click()
    assert pagina.formulario.razao_social.valor() == MATERIAIS.razao_social
    pagina.formulario.observacoes.definir("Entrega às terças.")
    pagina.formulario.salvar.click()
    assert obter_fornecedor(base.conexao, fornecedor_id).observacoes == "Entrega às terças."
    assert pagina.currentWidget() is pagina.ficha


def test_busca_e_inativos(aplicacao, base, monkeypatch):
    a = cadastrar_fornecedor(base.conexao, MATERIAIS)
    cadastrar_fornecedor(base.conexao, MARIA)
    pagina = PaginaFornecedores(base)
    pagina.lista.busca.setText("529.982")
    assert pagina.lista.tabela.rowCount() == 1
    pagina.lista.busca.setText("")
    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    pagina.abrir_ficha(a)
    pagina.ficha.ativar.click()
    assert not obter_fornecedor(base.conexao, a).ativo
    pagina.ficha.voltar.click()
    assert pagina.lista.tabela.rowCount() == 1
    pagina.lista.inativos.setChecked(True)
    assert pagina.lista.tabela.rowCount() == 2


def test_inativar_pede_confirmacao_e_excluir_so_sem_historico(aplicacao, base, monkeypatch):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(fornecedor_id)
    perguntas = []
    monkeypatch.setattr(telas, "perguntar", lambda *args: perguntas.append(args[1]) or False)
    pagina.ficha.ativar.click()
    pagina.ficha.excluir.click()
    assert perguntas == ["Inativar este fornecedor?", "Excluir este fornecedor?"]
    assert obter_fornecedor(base.conexao, fornecedor_id).ativo

    conta = salvar_conta_fornecedor(
        base.conexao, fornecedor_id, DadosContaFornecedor("001", "1234-5", "98765-4")
    )
    entidade = cadastrar_conta(base.conexao, DadosConta("Conta Movimento", "001", "1", "1-1"))
    base.conexao.execute(
        "INSERT INTO marcacao (conta_entidade_id, conta_fornecedor_id, criado_em)"
        " VALUES (?, ?, '2026-11-08T10:00:00')",
        (entidade, conta),
    )
    pagina.abrir_ficha(fornecedor_id)
    assert not pagina.ficha.excluir.isVisibleTo(pagina.ficha)

    outro = cadastrar_fornecedor(base.conexao, MARIA)
    pagina.abrir_ficha(outro)
    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    pagina.ficha.excluir.click()
    assert pagina.currentWidget() is pagina.lista
    assert [f.id for f in listar_fornecedores(base.conexao, incluir_inativos=True)] == [
        fornecedor_id
    ]


def test_conta_bancaria_pela_ficha(aplicacao, base, monkeypatch):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(fornecedor_id)
    ficha = pagina.ficha
    original = ficha.criar_dialogo_conta

    def criar(conta):
        dialogo = original(conta)
        dialogo.banco.definir("001")
        dialogo.agencia.definir("1234-5")
        dialogo.numero.definir("98765-4")
        dialogo.tipo.definir("corrente")
        return _sem_janela(dialogo)

    monkeypatch.setattr(ficha, "criar_dialogo_conta", criar)
    ficha.nova_conta.click()
    assert ficha.tabela_contas.rowCount() == 1
    assert ficha.tabela_contas.item(0, 0).text() == "001 · Banco do Brasil S.A."
    assert "11.222.333/0001-81" in "".join(
        w.text() for w in original(None).findChildren(type(ficha.titulo))
    )


def test_conta_repetida_em_outro_fornecedor_pede_confirmacao(aplicacao, base):
    a = cadastrar_fornecedor(base.conexao, MATERIAIS)
    b = cadastrar_fornecedor(base.conexao, MARIA)
    salvar_conta_fornecedor(base.conexao, a, DadosContaFornecedor("001", "1234-5", "98765-4"))
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(b)
    dialogo = pagina.ficha.criar_dialogo_conta(None)
    dialogo.banco.definir("001")
    dialogo.agencia.definir("1234-5")
    dialogo.numero.definir("98765-4")
    dialogo.confirmar.click()
    assert dialogo.aviso_repeticao.isVisibleTo(dialogo)
    assert "Distribuidora Exemplo" in dialogo.aviso_repeticao.text()
    assert dialogo.confirmar.text() == "Salvar mesmo assim"
    assert listar_contas_fornecedor(base.conexao, b) == []
    dialogo.confirmar.click()
    assert len(listar_contas_fornecedor(base.conexao, b)) == 1


def test_chave_pix_pela_ficha(aplicacao, base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(fornecedor_id)
    dialogo = pagina.ficha.criar_dialogo_chave(None)
    dialogo.tipo.definir("cnpj")
    assert dialogo.chave.valor() == "11.222.333/0001-81"
    dialogo.confirmar.click()
    dialogo = pagina.ficha.criar_dialogo_chave(None)
    dialogo.tipo.definir("email")
    dialogo.chave.definir("financeiro@")
    dialogo.confirmar.click()
    assert "E-mail inválido" in dialogo.chave.linha_ajuda.text()
    dialogo.chave.definir("financeiro@exemplo.com.br")
    dialogo.confirmar.click()
    assert [c.tipo for c in listar_chaves(base.conexao, fornecedor_id)] == ["cnpj", "email"]


def test_excluir_chave_sem_historico(aplicacao, base, monkeypatch):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(fornecedor_id)
    dialogo = pagina.ficha.criar_dialogo_chave(None)
    dialogo.tipo.definir("email")
    dialogo.chave.definir("financeiro@exemplo.com.br")
    dialogo.confirmar.click()
    chave = listar_chaves(base.conexao, fornecedor_id)[0]
    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    edicao = pagina.ficha.criar_dialogo_chave(chave)
    assert edicao.excluir is not None and edicao.ativar is None
    edicao.excluir.click()
    assert listar_chaves(base.conexao, fornecedor_id) == []
