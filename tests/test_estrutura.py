import subprocess
import sys

import baliza


def test_versao_definida():
    assert baliza.__version__ == "0.3.0"


def test_regras_e_dados_nao_dependem_da_interface():
    """RNF09: regras de negócio e dados funcionam sem carregar a biblioteca de telas."""
    codigo = "import sys, baliza.dominio, baliza.dados; print('PySide6' in sys.modules)"
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    )
    assert resultado.stdout.strip() == "False"
