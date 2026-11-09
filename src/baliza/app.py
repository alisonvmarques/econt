"""Ponto de entrada do Baliza."""

import os
import sys
import tempfile
from importlib import resources
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from baliza import __version__
from baliza.interface.janela_principal import JanelaPrincipal


def icone_do_baliza() -> QIcon:
    return QIcon(str(resources.files("baliza.interface").joinpath("icone.svg")))


def criar_aplicacao(argumentos: list[str] | None = None) -> QApplication:
    aplicacao = QApplication.instance() or QApplication(argumentos or sys.argv)
    aplicacao.setApplicationName("Baliza")
    aplicacao.setApplicationVersion(__version__)
    aplicacao.setWindowIcon(icone_do_baliza())
    return aplicacao


def verificar(relatorio: str | None = None) -> int:
    """Confere se o Baliza instalado abre: usado no teste automático dos instaladores.

    Cria dados de teste numa pasta temporária (nunca toca nos dados de verdade), abre a
    janela, confere a lista de bancos, a criptografia e os arquivos do tema, e fecha.
    Escreve o resultado no arquivo `relatorio`, porque o programa instalado no Windows
    não tem terminal para mostrar texto. Devolve 0 se tudo abriu.
    """
    linhas = [f"Baliza {__version__}"]
    codigo = 0
    anterior = os.environ.get("BALIZA_ARQUIVO")
    with tempfile.TemporaryDirectory() as pasta:
        os.environ["BALIZA_ARQUIVO"] = str(Path(pasta) / "verificacao.baliza")
        try:
            from baliza.dados.banco import BaseDeDados
            from baliza.dados.lista_bancos import listar_bancos
            from baliza.interface.tema import folha_de_estilo

            aplicacao = criar_aplicacao([sys.argv[0]])
            base = BaseDeDados.criar(Path(pasta) / "teste.baliza", "verificacao2026")[0]
            bancos = len(listar_bancos(base.conexao))
            reaberta = BaseDeDados.abrir(Path(pasta) / "teste.baliza", senha="verificacao2026")
            linhas.append(f"criptografia: ok (versão dos dados {reaberta.versao()})")
            linhas.append(f"bancos: {bancos}")
            if bancos < 400:
                raise RuntimeError("lista de bancos incompleta")
            folha_de_estilo()
            for arquivo in ("seta.svg", "marca.svg", "icone.svg"):
                if not resources.files("baliza.interface").joinpath(arquivo).is_file():
                    raise RuntimeError(f"arquivo do tema faltando: {arquivo}")
            linhas.append("tema: ok")
            janela = JanelaPrincipal()
            janela.show()
            aplicacao.processEvents()
            linhas.append(f"janela: {type(janela.tela_atual()).__name__}")
            janela.close()
            linhas.append("resultado: ok")
        except Exception as erro:  # noqa: BLE001 (o relatório precisa registrar qualquer falha)
            linhas.append(f"resultado: falhou ({type(erro).__name__}: {erro})")
            codigo = 1
        finally:
            if anterior is None:
                os.environ.pop("BALIZA_ARQUIVO", None)
            else:
                os.environ["BALIZA_ARQUIVO"] = anterior
    texto = "\n".join(linhas) + "\n"
    if relatorio:
        Path(relatorio).write_text(texto, encoding="utf-8")
    elif sys.stdout is not None:
        sys.stdout.write(texto)
    return codigo


MENSAGEM_DE_ERRO = (
    "Algo não saiu como esperado e esta ação não foi concluída. Os dados gravados antes "
    "continuam no arquivo. Se acontecer de novo, feche e abra o Baliza; se o problema for "
    "falta de espaço no disco, libere espaço antes de continuar."
)


def mensagem_de_erro_inesperado(erro: BaseException) -> str:
    """RNF04: em português, sem termos técnicos na frase principal."""
    if isinstance(erro, OSError) and getattr(erro, "errno", None) == 28:
        return (
            "Não há espaço no disco para gravar os dados. Libere espaço e repita a ação. "
            "Os dados gravados antes continuam no arquivo."
        )
    if isinstance(erro, PermissionError):
        return (
            "O Baliza não tem permissão para gravar na pasta dos dados. Confira as permissões "
            "da pasta e repita a ação. Os dados gravados antes continuam no arquivo."
        )
    return MENSAGEM_DE_ERRO


def avisar_erro_inesperado(tipo, erro, rastro) -> None:
    """Em vez de fechar sem explicação, mostra o que houve e deixa o Baliza aberto."""
    import traceback

    from PySide6.QtWidgets import QMessageBox

    caixa = QMessageBox()
    caixa.setIcon(QMessageBox.Icon.Warning)
    caixa.setWindowTitle("Baliza")
    caixa.setText(mensagem_de_erro_inesperado(erro))
    caixa.setDetailedText("".join(traceback.format_exception(tipo, erro, rastro)))
    caixa.exec()


def main() -> int:
    if "--verificar" in sys.argv:
        posicao = sys.argv.index("--verificar")
        relatorio = sys.argv[posicao + 1] if len(sys.argv) > posicao + 1 else None
        return verificar(relatorio)
    aplicacao = criar_aplicacao()
    sys.excepthook = avisar_erro_inesperado
    janela = JanelaPrincipal()
    janela.show()
    return aplicacao.exec()


if __name__ == "__main__":
    sys.exit(main())
