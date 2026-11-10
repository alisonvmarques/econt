from pathlib import Path

import pytest

from econt.dados.backup import listar_backups, pasta_de_backups
from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta
from econt.dados.entidade import Entidade, obter_entidade, salvar_entidade
from econt.dados.fornecedores import (
    DadosFornecedor,
    cadastrar_fornecedor,
    listar_fornecedores,
    salvar_chave_pix,
)
from econt.interface.area_principal import AreaPrincipal
from econt.interface.componentes import DURACAO_CONFIRMACAO_MS, Confirmacao, confirmar_rapido
from econt.interface.contas import PaginaContas
from econt.interface.janela_principal import JanelaPrincipal

SENHA = "fundo2026saude"


@pytest.fixture
def base(tmp_path):
    (tmp_path / "dados").mkdir()
    base = BaseDeDados.criar(tmp_path / "dados" / "dados.econt", SENHA)[0]
    salvar_entidade(base.conexao, Entidade("Fundo de Saúde Exemplo", "11.222.333/0001-81"))
    base.definir_configuracao("chave_de_recuperacao_guardada", "sim")
    base.salvar()
    return base


def test_inicio_mostra_o_resumo_e_orienta(aplicacao, base):
    area = AreaPrincipal(base)
    inicio = area.indice["inicio"]
    assert area.area_atual() == "inicio"
    assert [n.valor.text() for n in inicio.numeros] == ["0", "0", "0", "0"]
    avisos = [inicio.atencao.itemAt(i).widget().text() for i in range(inicio.atencao.count())]
    assert any("Comece pelas contas da entidade" in a for a in avisos)
    cadastrar_conta(base.conexao, DadosConta("Conta Movimento", "001", "1234-5", "55555-0"))
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    salvar_chave_pix(base.conexao, f, "cpf", "529.982.247-25")
    inicio.atualizar()
    assert [n.valor.text() for n in inicio.numeros] == ["1", "1", "1", "0"]
    assert inicio.numeros[0].rotulo.text() == "fornecedor ativo"
    avisos = [inicio.atencao.itemAt(i).widget().text() for i in range(inicio.atencao.count())]
    assert any("1 conta ou chave Pix ativa não está cadastrada" in a for a in avisos)


def test_atalhos_do_inicio(aplicacao, base):
    area = AreaPrincipal(base)
    inicio = area.indice["inicio"]
    inicio.consultar.click()
    assert area.area_atual() == "consulta"
    inicio.novo_fornecedor.click()
    assert area.area_atual() == "fornecedores"
    assert area.indice["fornecedores"].currentWidget() is area.indice["fornecedores"].formulario
    inicio.contas_entidade.click()
    assert area.area_atual() == "entidade"
    assert area.indice["entidade"].abas.currentIndex() == 1


def test_confirmacao_rapida_some_em_4_segundos(aplicacao, base):
    contas = PaginaContas(base)
    confirmacao = confirmar_rapido(contas, "Conta salva.")
    assert confirmacao.text() == "✓  Conta salva."
    assert confirmacao.relogio.interval() == DURACAO_CONFIRMACAO_MS == 4000
    assert confirmar_rapido(contas, "De novo.") is confirmacao  # uma só por janela
    confirmacao.relogio.timeout.emit()
    assert not confirmacao.isVisible()


def test_estado_vazio_das_contas_leva_ao_cadastro(aplicacao, base, monkeypatch):
    pagina = PaginaContas(base)
    assert pagina.lista.vazia.titulo.text() == "Nenhuma conta da entidade"
    abertos = []
    monkeypatch.setattr(pagina, "abrir_formulario", lambda conta: abertos.append(conta))
    pagina.lista.nova.clicked.disconnect()
    pagina.lista.nova.clicked.connect(lambda: pagina.abrir_formulario(None))
    pagina.lista.vazia.acao.click()
    assert abertos == [None]


def test_salvar_entidade_confirma(aplicacao, base):
    area = AreaPrincipal(base)
    area.navegacao.botoes["entidade"].click()
    pagina = area.indice["entidade"]
    pagina.salvar.click()
    confirmacao = area.findChild(Confirmacao, "confirmacao")
    assert confirmacao is not None and "Dados da entidade salvos" in confirmacao.text()
    assert obter_entidade(base.conexao).razao_social == "Fundo de Saúde Exemplo"


def test_fechar_a_janela_faz_backup(aplicacao, base):
    caminho = Path(base.cofre.caminho)
    base.fechar()
    janela = JanelaPrincipal(caminho)
    janela.tela_atual().senha.definir(SENHA)
    janela.tela_atual().entrar.click()
    assert isinstance(janela.tela_atual(), AreaPrincipal)
    janela.close()
    assert len(listar_backups(pasta_de_backups(caminho))) == 1


def test_exportar_e_restaurar_pela_tela(aplicacao, base, tmp_path, monkeypatch):
    caminho = Path(base.cofre.caminho)
    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    base.salvar()
    area = AreaPrincipal(base)
    pagina = area.indice["configuracoes"].backup
    pendrive = tmp_path / "pendrive"
    pendrive.mkdir()
    monkeypatch.setattr(pagina, "escolher_pasta", lambda: str(pendrive))
    pagina.exportar.click()
    exportado = listar_backups(pendrive)[0]
    assert str(pendrive) in pagina.retorno.text()
    assert pagina.retorno.property("aviso") == "sucesso"

    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "111.444.777-35", "Depois"))
    base.salvar()
    monkeypatch.setattr(pagina, "escolher_arquivo", lambda: str(exportado.caminho))
    restaurados = []
    area.restaurado.connect(restaurados.append)
    original = pagina.criar_dialogo_restaurar

    def criar(arquivo):
        dialogo = original(arquivo)
        dialogo.segredo.definir("senha-errada-1")
        dialogo.confirmar.click()
        assert "Senha incorreta" in dialogo.segredo.linha_ajuda.text() or dialogo.segredo.tem_erro()
        dialogo.segredo.definir(SENHA)
        dialogo.exec = lambda: (dialogo.confirmar.click(), dialogo.result())[1]
        return dialogo

    monkeypatch.setattr(pagina, "criar_dialogo_restaurar", criar)
    pagina.restaurar.click()
    assert len(restaurados) == 1
    assert [f.razao_social for f in listar_fornecedores(restaurados[0].conexao)] == ["Maria"]
    assert len(listar_backups(pasta_de_backups(caminho))) == 1  # os dados de antes


def test_copias_e_automatico_nas_configuracoes(aplicacao, base):
    area = AreaPrincipal(base)
    pagina = area.indice["configuracoes"].backup
    assert pagina.automatico.isChecked() and pagina.copias.value() == 7
    pagina.copias.setValue(3)
    assert base.configuracao("backup_copias") == "3"
    pagina.automatico.setChecked(False)
    assert base.configuracao("backup_automatico") == "nao"
    assert not pagina.copias.isEnabled()


def test_janela_troca_pelos_dados_restaurados(aplicacao, base, tmp_path):
    from econt.dados.backup import exportar, restaurar

    caminho = Path(base.cofre.caminho)
    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    base.salvar()
    copia = exportar(caminho, tmp_path / "copia")
    base.fechar()
    janela = JanelaPrincipal(caminho)
    janela.tela_atual().senha.definir(SENHA)
    janela.tela_atual().entrar.click()
    cadastrar_fornecedor(janela.base.conexao, DadosFornecedor("pf", "111.444.777-35", "Depois"))
    antiga = janela.area
    restaurada = restaurar(copia, caminho, senha=SENHA)
    antiga.restaurado.emit(restaurada)
    assert janela.base is restaurada
    assert janela.area is not antiga
    janela.close()  # não pode gravar os dados antigos por cima dos restaurados
    reaberta = BaseDeDados.abrir(caminho, senha=SENHA)
    assert [f.razao_social for f in listar_fornecedores(reaberta.conexao)] == ["Maria"]
