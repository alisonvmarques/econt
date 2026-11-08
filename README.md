# Baliza

Sistema desktop e offline para conferir as contas dos fornecedores e em quais contas da entidade estão cadastradas antes de pagar.

## Desenvolvimento

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
```
