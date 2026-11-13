"""Telas das Atividades (T28 a T31), sem janela visível."""

from datetime import date, timedelta

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt
from PySide6.QtGui import QDragMoveEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from econt.dados.atividades import (
    DadosAtividade,
    arquivar_atividade,
    criar_atividade,
    listar_arquivadas,
    listar_colunas,
    mover_atividade,
    obter_atividade,
    obter_quadro,
)
from econt.dados.banco import BaseDeDados
from econt.dados.fornecedores import DadosFornecedor, cadastrar_fornecedor
from econt.interface import atividades as telas
from econt.interface import dialogos_atividades as dialogos
from econt.interface.area_principal import AreaPrincipal
from econt.interface.atividades import TIPO_ARRASTE, PaginaAtividades
from econt.interface.dialogos_atividades import (
    DialogoArquivadas,
    DialogoAtividade,
    DialogoColuna,
)

SENHA = "fundo2026saude"
HOJE = date(2026, 11, 13)
A_FAZER, EM_ANDAMENTO, CONCLUIDO = 1, 2, 3


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


def _pagina(base) -> PaginaAtividades:
    pagina = PaginaAtividades(base, hoje=lambda: HOJE)
    pagina.resize(1200, 800)
    pagina.show()
    QApplication.processEvents()
    return pagina


def _titulos(base, coluna_id) -> list[str]:
    quadro = {item.coluna.id: item for item in obter_quadro(base.conexao, HOJE)}
    return [a.titulo for a in quadro[coluna_id].atividades]


def _na_tela(pagina, coluna_id) -> list[str]:
    return [c.atividade.titulo for c in pagina.coluna(coluna_id).visiveis()]


def _responder(monkeypatch, classe, preencher):
    """Troca o exec() do diálogo: preenche os campos e confirma, sem abrir janela."""

    def executar(dialogo):
        preencher(dialogo)
        if not dialogo.result():
            dialogo.ao_confirmar()
        return dialogo.result()

    monkeypatch.setattr(classe, "exec", executar)


def _arraste(atividade_id: int) -> QMimeData:
    dados = QMimeData()
    dados.setData(TIPO_ARRASTE, str(atividade_id).encode())
    return dados


def _ponto_antes(pagina, coluna_id, atividade_id) -> QPoint:
    """Um ponto na metade de cima do cartão: o cartão solto cai antes dele."""
    coluna = pagina.coluna(coluna_id)
    return pagina.cartao(atividade_id).mapTo(coluna, QPoint(20, 3))


def _ponto_no_fim(pagina, coluna_id) -> QPoint:
    coluna = pagina.coluna(coluna_id)
    return coluna.rolagem.mapTo(coluna, QPoint(20, coluna.rolagem.height() - 5))


def _soltar(pagina, coluna_id, atividade_id, ponto: QPoint) -> None:
    dados = _arraste(atividade_id)  # guardado: o evento não segura o objeto do Python
    evento = QDropEvent(
        QPointF(ponto),
        Qt.DropAction.MoveAction,
        dados,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    pagina.coluna(coluna_id).dropEvent(evento)
    QApplication.processEvents()


def test_area_na_navegacao_com_atalho(aplicacao, base):
    area = AreaPrincipal(base)
    botao = area.navegacao.botoes["atividades"]
    assert botao.text() == "Atividades"
    assert botao.toolTip() == "Atividades (Ctrl+5)"
    assert area.navegacao.botoes["configuracoes"].toolTip() == "Configurações (Ctrl+6)"
    botao.click()
    assert area.area_atual() == "atividades"
    pagina = area.indice["atividades"]
    assert [c.coluna.nome for c in pagina.colunas] == ["A fazer", "Em andamento", "Concluído"]
    assert "Nenhuma atividade ainda" in pagina.apoio.text()
    assert pagina.coluna(A_FAZER).vazia.isVisibleTo(pagina)


def test_cartao_mostra_titulo_prazo_e_fornecedor(aplicacao, base):
    c = base.conexao
    f = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora", nome_fantasia="Exemplo")
    )
    criar_atividade(c, A_FAZER, DadosAtividade("Atrasada", prazo=HOJE - timedelta(1)))
    criar_atividade(c, A_FAZER, DadosAtividade("Hoje", prazo=HOJE, fornecedor_id=f))
    criar_atividade(c, A_FAZER, DadosAtividade("Depois", prazo=HOJE + timedelta(7)))
    criar_atividade(c, CONCLUIDO, DadosAtividade("Feita", prazo=HOJE - timedelta(9)))
    pagina = _pagina(base)
    atrasada, hoje, depois = pagina.coluna(A_FAZER).cartoes
    assert atrasada.prazo.text() == "⚠ Atrasada · prazo 12/11/2026"
    assert atrasada.property("prazo") == "atrasada"
    assert atrasada.prazo.property("etiqueta") == "perigo"
    assert hoje.prazo.text() == "⏱ Vence hoje" and hoje.prazo.property("etiqueta") == "atencao"
    assert hoje.fornecedor.text() == "Exemplo"
    assert depois.prazo.text() == "Prazo 20/11/2026" and depois.prazo.property("etiqueta") is None
    (feita,) = pagina.coluna(CONCLUIDO).cartoes
    assert feita.property("prazo") == "concluida" and feita.prazo.text().startswith("✓")
    assert pagina.coluna(A_FAZER).quantidade.text() == "3"
    assert "Hoje" in hoje.accessibleName() and "Exemplo" in hoje.accessibleName()


def test_criar_e_editar_pela_interface(aplicacao, base, monkeypatch):
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    pagina = _pagina(base)

    def nova(dialogo):
        dialogo.titulo.definir("Conferir notas")
        dialogo.descricao.caixa.setPlainText("Notas de outubro\ne de novembro")
        dialogo.prazo.definir("20/11/2026")
        dialogo.fornecedor.definir(f)

    _responder(monkeypatch, DialogoAtividade, nova)
    pagina.coluna(EM_ANDAMENTO).nova_atividade.click()
    (atividade,) = obter_quadro(base.conexao, HOJE)[1].atividades
    assert (atividade.titulo, atividade.prazo, atividade.fornecedor_id) == (
        "Conferir notas",
        date(2026, 11, 20),
        f,
    )
    assert atividade.descricao == "Notas de outubro\ne de novembro"
    assert _na_tela(pagina, EM_ANDAMENTO) == ["Conferir notas"]
    # Gravado no disco, não só na memória.
    assert _titulos(BaseDeDados.abrir(base.cofre.caminho, senha=SENHA), EM_ANDAMENTO) == [
        "Conferir notas"
    ]

    def editar(dialogo):
        assert dialogo.titulo.valor() == "Conferir notas"
        assert dialogo.prazo.valor() == "20/11/2026"
        dialogo.titulo.definir("Conferir notas fiscais")
        dialogo.prazo.definir("")
        dialogo.fornecedor.caixa.setEditText("")

    _responder(monkeypatch, DialogoAtividade, editar)
    pagina.abrir_atividade(atividade.id)
    editada = obter_atividade(base.conexao, atividade.id)
    assert (editada.titulo, editada.prazo, editada.fornecedor_id) == (
        "Conferir notas fiscais",
        None,
        None,
    )


def test_erros_aparecem_no_campo(aplicacao, base):
    pagina = _pagina(base)
    dialogo = pagina.criar_dialogo_atividade(A_FAZER, None)
    dialogo.prazo.definir("2026-11-20")
    dialogo.fornecedor.caixa.setEditText("Ninguém")
    dialogo.ao_confirmar()
    assert not dialogo.result()
    assert dialogo.titulo.tem_erro() and "Informe o título" in dialogo.titulo.linha_ajuda.text()
    assert "assim: 25/11/2026" in dialogo.prazo.linha_ajuda.text()
    assert "Escolha um fornecedor da lista" in dialogo.fornecedor.linha_ajuda.text()
    assert obter_quadro(base.conexao)[0].atividades == []


def test_fornecedor_inativo_aparece_no_dialogo(aplicacao, base):
    from econt.dados.fornecedores import definir_fornecedor_ativo

    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    a = criar_atividade(base.conexao, A_FAZER, DadosAtividade("Pagar", fornecedor_id=f))
    definir_fornecedor_ativo(base.conexao, f, False)
    pagina = _pagina(base)
    assert pagina.cartao(a).fornecedor.text() == "Maria (inativo)"
    dialogo = pagina.criar_dialogo_atividade(0, a)
    assert dialogo.fornecedor.caixa.currentText() == "Maria (inativo)"
    dialogo.ao_confirmar()
    assert obter_atividade(base.conexao, a).fornecedor_id == f


def test_arquivar_restaurar_e_excluir_pela_interface(aplicacao, base, monkeypatch):
    a, b = (criar_atividade(base.conexao, A_FAZER, DadosAtividade(t)) for t in ("A", "B"))
    pagina = _pagina(base)
    perguntas = []
    monkeypatch.setattr(telas, "perguntar", lambda *args: perguntas.append(args[1]) or False)
    pagina.arquivar(a)
    assert perguntas == ["Arquivar atividade"] and _titulos(base, A_FAZER) == ["A", "B"]

    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    _responder(monkeypatch, DialogoAtividade, lambda d: d.arquivar.click())
    pagina.abrir_atividade(a)  # o botão Arquivar do diálogo
    assert _na_tela(pagina, A_FAZER) == ["B"]
    assert [x.titulo for x in listar_arquivadas(base.conexao)] == ["A"]

    arquivadas = DialogoArquivadas(pagina, base)
    assert arquivadas.tabela.rowCount() == 1
    assert arquivadas.tabela.item(0, 1).text() == "A fazer"
    arquivadas.restaurar.click()
    assert arquivadas.mudou and arquivadas.vazia.isVisibleTo(arquivadas)
    assert _titulos(base, A_FAZER) == ["B", "A"]

    arquivar_atividade(base.conexao, b)
    arquivadas = DialogoArquivadas(pagina, base)
    monkeypatch.setattr(dialogos, "perguntar", lambda *args: perguntas.append(args[1]) or False)
    arquivadas.excluir.click()
    assert perguntas[-1] == "Excluir definitivamente" and listar_arquivadas(base.conexao)
    monkeypatch.setattr(dialogos, "perguntar", lambda *args: True)
    arquivadas.excluir.click()
    assert listar_arquivadas(base.conexao) == []


def test_mostrar_arquivadas_atualiza_o_quadro(aplicacao, base, monkeypatch):
    a = criar_atividade(base.conexao, A_FAZER, DadosAtividade("A"))
    arquivar_atividade(base.conexao, a)
    pagina = _pagina(base)
    _responder(monkeypatch, DialogoArquivadas, lambda d: d.restaurar.click())
    pagina.arquivadas.click()
    assert _na_tela(pagina, A_FAZER) == ["A"]


def test_mover_pelo_teclado(aplicacao, base):
    ids = [criar_atividade(base.conexao, A_FAZER, DadosAtividade(t)) for t in "ABC"]
    criar_atividade(base.conexao, EM_ANDAMENTO, DadosAtividade("X"))
    pagina = _pagina(base)
    pagina.activateWindow()
    QTest.qWaitForWindowActive(pagina)
    controle = Qt.KeyboardModifier.ControlModifier

    pagina.focar(ids[2])
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Up, controle)
    assert _titulos(base, A_FAZER) == ["A", "C", "B"]
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Up, controle)
    assert _titulos(base, A_FAZER) == ["C", "A", "B"]
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Up, controle)  # já é a primeira
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Down, controle)
    assert _titulos(base, A_FAZER) == ["A", "C", "B"]
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Right, controle)
    assert _titulos(base, EM_ANDAMENTO) == ["X", "C"]  # fim da coluna vizinha
    assert QApplication.focusWidget() is pagina.cartao(ids[2])
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Right, controle)
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Right, controle)  # já é a última
    assert _titulos(base, CONCLUIDO) == ["C"]
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Left, controle)
    assert _titulos(base, EM_ANDAMENTO) == ["X", "C"]
    assert _na_tela(pagina, EM_ANDAMENTO) == ["X", "C"]


def test_menu_do_cartao_oferece_as_mesmas_acoes(aplicacao, base):
    a = criar_atividade(base.conexao, A_FAZER, DadosAtividade("A"))
    pagina = _pagina(base)
    menu = pagina.cartao(a).criar_menu()
    acoes = {x.text(): x for x in menu.actions() if x.text()}
    assert list(acoes) == [
        "Abrir",
        "Mover para a coluna anterior",
        "Mover para a próxima coluna",
        "Subir na coluna",
        "Descer na coluna",
        "Arquivar…",
    ]
    assert acoes["Mover para a próxima coluna"].shortcut().toString() == "Ctrl+Right"
    acoes["Mover para a próxima coluna"].trigger()
    assert _titulos(base, EM_ANDAMENTO) == ["A"]


@pytest.mark.filterwarnings("ignore::DeprecationWarning")  # QDragMoveEvent do Qt 6
def test_arrastar_e_soltar_em_posicao_especifica(aplicacao, base):
    a, b = (criar_atividade(base.conexao, A_FAZER, DadosAtividade(t)) for t in "AB")
    x, y, z = (criar_atividade(base.conexao, EM_ANDAMENTO, DadosAtividade(t)) for t in "XYZ")
    pagina = _pagina(base)

    coluna = pagina.coluna(EM_ANDAMENTO)
    ponto = _ponto_antes(pagina, EM_ANDAMENTO, y)
    dados = _arraste(a)
    coluna.dragMoveEvent(
        QDragMoveEvent(
            ponto,
            Qt.DropAction.MoveAction,
            dados,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert coluna.indicador.isVisibleTo(coluna) and coluna.antes_de_indicado == y

    _soltar(pagina, EM_ANDAMENTO, a, ponto)
    assert _titulos(base, EM_ANDAMENTO) == ["X", "A", "Y", "Z"]
    assert _na_tela(pagina, EM_ANDAMENTO) == ["X", "A", "Y", "Z"]  # recarregado da base
    _soltar(pagina, EM_ANDAMENTO, x, _ponto_no_fim(pagina, EM_ANDAMENTO))  # mesma coluna
    assert _titulos(base, EM_ANDAMENTO) == ["A", "Y", "Z", "X"]
    _soltar(pagina, EM_ANDAMENTO, z, _ponto_antes(pagina, EM_ANDAMENTO, a))
    assert _titulos(base, EM_ANDAMENTO) == ["Z", "A", "Y", "X"]
    _soltar(pagina, CONCLUIDO, b, _ponto_no_fim(pagina, CONCLUIDO))  # coluna vazia
    assert _titulos(base, CONCLUIDO) == ["B"] and _titulos(base, A_FAZER) == []
    assert not pagina.coluna(EM_ANDAMENTO).indicador.isVisibleTo(pagina)


def test_busca_filtra_e_arrastar_respeita_a_ordem_real(aplicacao, base):
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("Pagar energia", "conta de luz"))
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("Conferir notas", fornecedor_id=f))
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("Pagar água"))
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("Pagar aluguel"))
    novo = criar_atividade(base.conexao, EM_ANDAMENTO, DadosAtividade("Pagar internet"))
    pagina = _pagina(base)

    pagina.busca.setText("LUZ")
    assert _na_tela(pagina, A_FAZER) == ["Pagar energia"]
    pagina.busca.setText("maria")
    assert _na_tela(pagina, A_FAZER) == ["Conferir notas"]
    assert pagina.coluna(A_FAZER).quantidade.text() == "1 de 4"
    assert pagina.coluna(EM_ANDAMENTO).vazia.text() == "Nenhuma atividade encontrada nesta coluna."
    pagina.busca.setText("xyz")
    assert "Nenhuma atividade encontrada para “xyz”" in pagina.apoio.text()

    # Com "pagar", Conferir notas (2ª) some. Soltar antes de Pagar água cai na 3ª posição real.
    pagina.busca.setText("pagar")
    assert _na_tela(pagina, A_FAZER) == ["Pagar energia", "Pagar água", "Pagar aluguel"]
    _soltar(pagina, A_FAZER, novo, _ponto_antes(pagina, A_FAZER, 3))
    assert _titulos(base, A_FAZER) == [
        "Pagar energia",
        "Conferir notas",
        "Pagar internet",
        "Pagar água",
        "Pagar aluguel",
    ]
    assert _na_tela(pagina, A_FAZER) == [
        "Pagar energia",
        "Pagar internet",
        "Pagar água",
        "Pagar aluguel",
    ]
    pagina.busca.clear()
    assert len(_na_tela(pagina, A_FAZER)) == 5


def test_colunas_pela_interface(aplicacao, base, monkeypatch):
    pagina = _pagina(base)

    _responder(monkeypatch, DialogoColuna, lambda d: d.nome.definir("Concluído"))
    pagina.nova_coluna.click()
    assert len(listar_colunas(base.conexao)) == 3  # nome repetido não passa

    def nova(dialogo):
        dialogo.nome.definir("Pago")
        dialogo.conclusao.setChecked(True)

    _responder(monkeypatch, DialogoColuna, nova)
    pagina.nova_coluna.click()
    assert [(k.nome, k.conclusao) for k in listar_colunas(base.conexao)][-2:] == [
        ("Concluído", False),
        ("Pago", True),
    ]
    pago = listar_colunas(base.conexao)[-1].id
    pagina.mover_coluna(pago, -1)
    assert [c.coluna.nome for c in pagina.colunas] == [
        "A fazer",
        "Em andamento",
        "Pago",
        "Concluído",
    ]

    avisos = []
    monkeypatch.setattr(telas, "avisar", lambda *args: avisos.append(args[2]))
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("A"))
    pagina.atualizar()
    pagina.excluir_coluna(A_FAZER)
    assert "Mova ou exclua as atividades" in avisos[-1]
    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    pagina.excluir_coluna(pago)
    assert [c.coluna.nome for c in pagina.colunas] == ["A fazer", "Em andamento", "Concluído"]


def test_inicio_avisa_atrasadas_e_de_hoje(aplicacao, base):
    hoje = date.today()
    area = AreaPrincipal(base)
    inicio = area.indice["inicio"]

    def avisos():
        return [inicio.atencao.itemAt(i).widget().text() for i in range(inicio.atencao.count())]

    assert not any("atividade" in a for a in avisos())
    atrasada = criar_atividade(
        base.conexao, A_FAZER, DadosAtividade("Atrasada", prazo=hoje - timedelta(days=3))
    )
    criar_atividade(base.conexao, A_FAZER, DadosAtividade("Hoje", prazo=hoje))
    inicio.atualizar()
    assert any("1 atividade atrasada" in a for a in avisos())
    assert any("1 atividade vence hoje" in a for a in avisos())
    mover_atividade(base.conexao, atrasada, CONCLUIDO, 1)
    inicio.atualizar()
    assert not any("atrasada" in a for a in avisos())
    assert any("vence hoje" in a for a in avisos())


def test_quadro_so_e_remontado_quando_o_arraste_termina(aplicacao, base):
    a, b = (criar_atividade(base.conexao, A_FAZER, DadosAtividade(t)) for t in "AB")
    pagina = _pagina(base)
    arrastado = pagina.cartao(a)
    arrastado.acao.emit("arraste", a)
    _soltar(pagina, EM_ANDAMENTO, a, _ponto_no_fim(pagina, EM_ANDAMENTO))
    assert _titulos(base, EM_ANDAMENTO) == ["A"]  # gravado na hora
    assert pagina.cartao(a) is arrastado  # mas o cartão arrastado continua de pé
    arrastado.acao.emit("fim_do_arraste", a)
    assert _na_tela(pagina, EM_ANDAMENTO) == ["A"] and _na_tela(pagina, A_FAZER) == ["B"]
    assert pagina.cartao(a) is not arrastado


def test_fornecedor_aparece_enquanto_digita(aplicacao, base):
    c = base.conexao
    cadastrar_fornecedor(c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo"))
    lab = cadastrar_fornecedor(
        c,
        DadosFornecedor(
            "pj", "11.444.777/0001-61", "Laboratório Modelo Ltda", nome_fantasia="Lab Saúde"
        ),
    )
    pagina = _pagina(base)
    dialogo = pagina.criar_dialogo_atividade(A_FAZER, None)
    dialogo.show()
    campo = dialogo.fornecedor
    assert campo.caixa.currentText() == ""  # sem fornecedor: vazio, pronto para digitar
    QTest.keyClicks(campo.caixa.lineEdit(), "laboratorio")
    assert campo.sugestoes() == ["Laboratório Modelo Ltda (Lab Saúde)"]
    campo.caixa.lineEdit().clear()
    QTest.keyClicks(campo.caixa.lineEdit(), "SAUDE")  # sem acento e em maiúsculas
    assert campo.sugestoes() == ["Laboratório Modelo Ltda (Lab Saúde)"]
    campo.caixa.lineEdit().clear()
    QTest.keyClicks(campo.caixa.lineEdit(), "11444")  # pelo CNPJ
    assert campo.sugestoes() == ["Laboratório Modelo Ltda (Lab Saúde)"]
    popup = campo.caixa.completer().popup()
    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Return)
    assert campo.valor() == lab
    dialogo.titulo.definir("Pedir certidão")
    dialogo.ao_confirmar()
    assert obter_atividade(c, dialogo.atividade_id).fornecedor_id == lab
