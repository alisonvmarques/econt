import subprocess
import sys

import econt


def test_versao_definida():
    assert econt.__version__ == "1.0.0"


def test_regras_e_dados_nao_dependem_da_interface():
    """RNF09: regras de negócio e dados funcionam sem carregar a biblioteca de telas."""
    codigo = "import sys, econt.dominio, econt.dados; print('PySide6' in sys.modules)"
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    )
    assert resultado.stdout.strip() == "False"
