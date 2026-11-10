"""Troca de nome do sistema (novembro de 2026): os dados gravados antes continuam abrindo."""

import os

import pytest

from econt.dados import local
from econt.dados.backup import listar_backups
from econt.dados.banco import BaseDeDados
from econt.dados.cofre import MAGICO, MAGICO_ANTERIOR, Cofre, SenhaIncorreta

SENHA = "senhaforte2026"


def _arquivo_anterior(caminho, dados=b"dados de antes"):
    """Arquivo como o sistema gravava antes da troca de nome."""
    cofre, chave = Cofre.criar(caminho, SENHA)
    cofre._magico = MAGICO_ANTERIOR
    cofre._cabecalho["senha"] = _embrulhar_anterior(cofre, SENHA)
    cofre._cabecalho["recuperacao"] = _embrulhar_anterior(cofre, chave.replace("-", ""))
    cofre.gravar(dados)
    return chave


def _embrulhar_anterior(cofre, segredo):
    from econt.dados.cofre import _embrulhar

    return _embrulhar(cofre._chave_dados, segredo, MAGICO_ANTERIOR)


def test_arquivo_novo_usa_a_assinatura_nova(tmp_path):
    Cofre.criar(tmp_path / "novo.econt", SENHA)
    assert (tmp_path / "novo.econt").read_bytes().startswith(MAGICO)
    assert len(MAGICO) == len(MAGICO_ANTERIOR)


def test_arquivo_anterior_abre_com_a_senha_e_com_a_chave(tmp_path):
    caminho = tmp_path / "dados.baliza"
    chave = _arquivo_anterior(caminho)
    assert caminho.read_bytes().startswith(MAGICO_ANTERIOR)
    assert Cofre.abrir_com_senha(caminho, SENHA).ler() == b"dados de antes"
    assert Cofre.abrir_com_chave(caminho, chave).ler() == b"dados de antes"
    with pytest.raises(SenhaIncorreta):
        Cofre.abrir_com_senha(caminho, "outrasenha2026")


def test_arquivo_anterior_continua_gravando_e_trocando_senha(tmp_path):
    caminho = tmp_path / "dados.baliza"
    chave = _arquivo_anterior(caminho)
    cofre = Cofre.abrir_com_senha(caminho, SENHA)
    cofre.gravar(b"dados novos")
    cofre.trocar_senha("senhanova2026")
    assert Cofre.abrir_com_senha(caminho, "senhanova2026").ler() == b"dados novos"
    assert Cofre.abrir_com_chave(caminho, chave).ler() == b"dados novos"
    nova = Cofre.abrir_com_senha(caminho, "senhanova2026").gerar_nova_chave()
    assert Cofre.abrir_com_chave(caminho, nova).ler() == b"dados novos"


def test_copia_os_dados_e_os_backups_da_pasta_anterior_sem_apagar(tmp_path):
    origem, destino = tmp_path / "baliza", tmp_path / "econt"
    origem.mkdir()
    BaseDeDados.criar(origem / "dados.baliza", SENHA)[0].fechar()
    (origem / "backups").mkdir()
    (origem / "backups" / "baliza-20261108-180000.baliza").write_bytes(
        (origem / "dados.baliza").read_bytes()
    )
    antes = sorted(p.name for p in origem.rglob("*"))

    assert local.trazer_dados_anteriores(origem, destino)

    assert (destino / "dados.econt").read_bytes() == (origem / "dados.baliza").read_bytes()
    BaseDeDados.abrir(destino / "dados.econt", senha=SENHA).fechar()
    assert [b.caminho.name for b in listar_backups(destino / "backups")] == [
        "econt-20261108-180000.econt"
    ]
    assert sorted(p.name for p in origem.rglob("*")) == antes


def test_nao_copia_de_novo_nem_sobrescreve(tmp_path):
    origem, destino = tmp_path / "baliza", tmp_path / "econt"
    origem.mkdir()
    destino.mkdir()
    (origem / "dados.baliza").write_bytes(b"antigo")
    (destino / "dados.econt").write_bytes(b"atual")
    assert not local.trazer_dados_anteriores(origem, destino)
    assert (destino / "dados.econt").read_bytes() == b"atual"
    assert not local.trazer_dados_anteriores(tmp_path / "nada", tmp_path / "vazio")


def test_com_arquivo_escolhido_nao_mexe_em_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("ECONT_ARQUIVO", str(tmp_path / "outro.econt"))
    monkeypatch.setattr(local, "pasta_anterior", lambda: tmp_path / "baliza")
    assert not local.trazer_dados_anteriores()


def test_pastas_por_sistema(monkeypatch, tmp_path):
    monkeypatch.setattr(local.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert local.pasta_de_dados() == tmp_path / "econt"
    assert local.pasta_anterior() == tmp_path / "baliza"
    monkeypatch.setattr(local.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert local.pasta_de_dados() == tmp_path / "ECont"
    assert os.path.basename(local.pasta_anterior()) == "Baliza"
