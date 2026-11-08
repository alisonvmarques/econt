"""Arquivo de dados criptografado do Baliza (RNF12).

Como funciona:
- Os dados são cifrados com uma chave aleatória de 256 bits (a chave dos dados), usando AES-256-GCM.
- A chave dos dados é guardada no próprio arquivo duas vezes, cada uma cifrada por uma chave
  derivada (scrypt) de um segredo diferente: a senha e a chave de recuperação.
- Assim, a senha e a chave de recuperação abrem o mesmo arquivo (RF20, RF21), e trocar a senha
  não exige cifrar os dados de novo.

Formato do arquivo: MAGICO + tamanho do cabeçalho (4 bytes) + cabeçalho JSON + dados cifrados.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import struct
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGICO = b"BALIZA\x00\x01"
VERSAO_FORMATO = 1
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 1

# Sem I, O, 0 e 1, para não confundir ao copiar da folha impressa.
ALFABETO_CHAVE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TAMANHO_CHAVE = 24


class ErroDeArquivo(Exception):
    """Erro ao abrir ou gravar o arquivo de dados."""


class SenhaIncorreta(ErroDeArquivo):
    def __init__(self) -> None:
        super().__init__("Senha incorreta. Confira e tente de novo.")


class ChaveIncorreta(ErroDeArquivo):
    def __init__(self) -> None:
        super().__init__("Chave de recuperação inválida. Confira as letras e os números.")


class ArquivoInvalido(ErroDeArquivo):
    def __init__(self) -> None:
        super().__init__("Este arquivo não é um arquivo de dados do Baliza ou está danificado.")


def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def _de_b64(texto: str) -> bytes:
    return base64.b64decode(texto.encode("ascii"))


def gerar_chave_recuperacao() -> str:
    """Gera uma chave no formato XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (120 bits)."""
    letras = "".join(secrets.choice(ALFABETO_CHAVE) for _ in range(TAMANHO_CHAVE))
    return "-".join(letras[i : i + 4] for i in range(0, TAMANHO_CHAVE, 4))


def normalizar_chave(chave: str) -> str:
    """Aceita a chave com ou sem traços, espaços e letras minúsculas."""
    return "".join(c for c in chave.upper() if c.isalnum())


def _derivar(segredo: str, sal: bytes) -> bytes:
    kdf = Scrypt(salt=sal, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(segredo.encode("utf-8"))


def _embrulhar(chave_dados: bytes, segredo: str) -> dict[str, str]:
    sal, nonce = os.urandom(16), os.urandom(12)
    cifrada = AESGCM(_derivar(segredo, sal)).encrypt(nonce, chave_dados, MAGICO)
    return {"sal": _b64(sal), "nonce": _b64(nonce), "chave": _b64(cifrada)}


def _desembrulhar(embrulho: dict[str, str], segredo: str) -> bytes:
    chave = _derivar(segredo, _de_b64(embrulho["sal"]))
    return AESGCM(chave).decrypt(_de_b64(embrulho["nonce"]), _de_b64(embrulho["chave"]), MAGICO)


@dataclass
class Cofre:
    """Arquivo de dados aberto. Guarda a chave dos dados só na memória."""

    caminho: Path
    _chave_dados: bytes
    _cabecalho: dict

    @classmethod
    def criar(cls, caminho: str | os.PathLike, senha: str, dados: bytes = b"") -> tuple[Cofre, str]:
        """Cria um arquivo novo. Devolve o cofre aberto e a chave de recuperação."""
        caminho = Path(caminho)
        if caminho.exists():
            raise ErroDeArquivo(f"Já existe um arquivo em {caminho}.")
        chave_recuperacao = gerar_chave_recuperacao()
        chave_dados = AESGCM.generate_key(bit_length=256)
        cabecalho = {
            "versao": VERSAO_FORMATO,
            "kdf": {"nome": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
            "senha": _embrulhar(chave_dados, senha),
            "recuperacao": _embrulhar(chave_dados, normalizar_chave(chave_recuperacao)),
        }
        cofre = cls(caminho, chave_dados, cabecalho)
        cofre.gravar(dados)
        return cofre, chave_recuperacao

    @classmethod
    def abrir_com_senha(cls, caminho: str | os.PathLike, senha: str) -> Cofre:
        cabecalho, _ = _ler_arquivo(Path(caminho))
        try:
            chave_dados = _desembrulhar(cabecalho["senha"], senha)
        except InvalidTag:
            raise SenhaIncorreta() from None
        return cls(Path(caminho), chave_dados, cabecalho)

    @classmethod
    def abrir_com_chave(cls, caminho: str | os.PathLike, chave_recuperacao: str) -> Cofre:
        cabecalho, _ = _ler_arquivo(Path(caminho))
        try:
            chave_dados = _desembrulhar(
                cabecalho["recuperacao"], normalizar_chave(chave_recuperacao)
            )
        except InvalidTag:
            raise ChaveIncorreta() from None
        return cls(Path(caminho), chave_dados, cabecalho)

    def ler(self) -> bytes:
        cabecalho, conteudo = _ler_arquivo(self.caminho)
        try:
            return AESGCM(self._chave_dados).decrypt(_de_b64(cabecalho["nonce"]), conteudo, MAGICO)
        except InvalidTag:
            raise ArquivoInvalido() from None

    def gravar(self, dados: bytes) -> None:
        """Cifra e grava os dados. A gravação é atômica: ou o arquivo novo, ou o antigo."""
        nonce = os.urandom(12)
        cifrado = AESGCM(self._chave_dados).encrypt(nonce, dados, MAGICO)
        self._cabecalho["nonce"] = _b64(nonce)
        cabecalho = json.dumps(self._cabecalho, separators=(",", ":")).encode("utf-8")
        temporario = self.caminho.with_name(self.caminho.name + ".tmp")
        with open(temporario, "wb") as arquivo:
            arquivo.write(MAGICO + struct.pack(">I", len(cabecalho)) + cabecalho + cifrado)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, self.caminho)

    def trocar_senha(self, nova_senha: str) -> None:
        self._cabecalho["senha"] = _embrulhar(self._chave_dados, nova_senha)
        self.gravar(self.ler())

    def gerar_nova_chave(self) -> str:
        """Gera uma chave de recuperação nova. A anterior deixa de funcionar."""
        chave = gerar_chave_recuperacao()
        self._cabecalho["recuperacao"] = _embrulhar(self._chave_dados, normalizar_chave(chave))
        self.gravar(self.ler())
        return chave


def _ler_arquivo(caminho: Path) -> tuple[dict, bytes]:
    try:
        bruto = caminho.read_bytes()
    except FileNotFoundError:
        raise ErroDeArquivo(f"Arquivo de dados não encontrado: {caminho}") from None
    if not bruto.startswith(MAGICO) or len(bruto) < len(MAGICO) + 4:
        raise ArquivoInvalido()
    inicio = len(MAGICO) + 4
    (tamanho,) = struct.unpack(">I", bruto[len(MAGICO) : inicio])
    try:
        cabecalho = json.loads(bruto[inicio : inicio + tamanho].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ArquivoInvalido() from None
    if cabecalho.get("versao") != VERSAO_FORMATO:
        raise ArquivoInvalido()
    return cabecalho, bruto[inicio + tamanho :]
