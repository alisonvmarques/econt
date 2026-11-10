from datetime import datetime, timedelta

import pytest

from econt.dados.backup import (
    BACKUP_AUTOMATICO,
    COPIAS,
    backup_ao_fechar,
    exportar,
    fazer_backup,
    listar_backups,
    manter_ultimas,
    pasta_de_backups,
    restaurar,
)
from econt.dados.banco import BaseDeDados
from econt.dados.cofre import SenhaIncorreta
from econt.dados.fornecedores import (
    DadosFornecedor,
    cadastrar_fornecedor,
    listar_fornecedores,
)

SENHA = "fundo2026saude"
INICIO = datetime(2026, 11, 8, 18, 0)


@pytest.fixture
def dados(tmp_path):
    caminho = tmp_path / "dados" / "dados.econt"
    caminho.parent.mkdir()
    base, chave = BaseDeDados.criar(caminho, SENHA)
    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo"))
    base.salvar()
    return base, caminho, chave


def test_backup_a_cada_fechamento_guardando_sete(dados):
    base, caminho, _ = dados
    for minuto in range(9):
        backup_ao_fechar(base, caminho, INICIO + timedelta(minutes=minuto))
    backups = listar_backups(pasta_de_backups(caminho))
    assert len(backups) == 7
    assert backups[0].quando == INICIO + timedelta(minutes=8)
    assert backups[-1].quando == INICIO + timedelta(minutes=2)


def test_quantidade_de_copias_pode_mudar(dados):
    base, caminho, _ = dados
    base.definir_configuracao(COPIAS, "3")
    for minuto in range(5):
        backup_ao_fechar(base, caminho, INICIO + timedelta(minutes=minuto))
    assert len(listar_backups(pasta_de_backups(caminho))) == 3
    base.definir_configuracao(BACKUP_AUTOMATICO, "nao")
    assert backup_ao_fechar(base, caminho, INICIO + timedelta(hours=1)) is None


def test_backup_e_criptografado_como_o_original(dados):
    base, caminho, chave = dados
    feito = fazer_backup(caminho, pasta_de_backups(caminho), INICIO)
    assert b"Maria Exemplo" not in feito.read_bytes()
    assert feito.read_bytes() == caminho.read_bytes()
    with pytest.raises(SenhaIncorreta):
        BaseDeDados.abrir(feito, senha="outra-senha-123")
    assert BaseDeDados.abrir(feito, chave=chave).versao() == base.versao()


def test_manter_ignora_arquivos_que_nao_sao_backups(dados):
    _, caminho, _ = dados
    pasta = pasta_de_backups(caminho)
    fazer_backup(caminho, pasta, INICIO)
    (pasta / "anotacoes.txt").write_text("não mexer")
    manter_ultimas(pasta, 1)
    assert (pasta / "anotacoes.txt").exists()


def test_exportar_para_outro_lugar(dados, tmp_path):
    _, caminho, _ = dados
    pendrive = tmp_path / "pendrive"
    feito = exportar(caminho, pendrive, INICIO)
    assert feito == pendrive / "econt-20261108-180000.econt"
    assert listar_backups(pendrive)[0].tamanho == caminho.stat().st_size


def test_restaurar_com_a_senha_do_backup(dados):
    base, caminho, _ = dados
    feito = fazer_backup(caminho, pasta_de_backups(caminho), INICIO)
    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "111.444.777-35", "Depois"))
    base.salvar()
    assert len(listar_fornecedores(base.conexao)) == 2
    restaurada = restaurar(feito, caminho, senha=SENHA, quando=INICIO + timedelta(hours=1))
    assert [f.razao_social for f in listar_fornecedores(restaurada.conexao)] == ["Maria Exemplo"]
    # os dados de antes da restauração viraram um backup
    antes = listar_backups(pasta_de_backups(caminho))[0]
    assert antes.quando == INICIO + timedelta(hours=1)
    assert len(listar_fornecedores(BaseDeDados.abrir(antes.caminho, senha=SENHA).conexao)) == 2


def test_restaurar_com_senha_errada_nao_muda_nada(dados):
    base, caminho, chave = dados
    feito = fazer_backup(caminho, pasta_de_backups(caminho), INICIO)
    original = caminho.read_bytes()
    with pytest.raises(SenhaIncorreta):
        restaurar(feito, caminho, senha="senha-errada-1")
    assert caminho.read_bytes() == original
    assert len(listar_backups(pasta_de_backups(caminho))) == 1
    assert restaurar(feito, caminho, chave=chave).versao() == base.versao()


def test_tamanho_legivel(tmp_path):
    from econt.dados.backup import Backup

    assert Backup(tmp_path, INICIO, 184_000).tamanho_legivel == "180 KB"
    assert Backup(tmp_path, INICIO, 300).tamanho_legivel == "1 KB"
    assert Backup(tmp_path, INICIO, 3 * 1024 * 1024 + 200_000).tamanho_legivel == "3,2 MB"
