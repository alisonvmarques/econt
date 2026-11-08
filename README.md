# Baliza

[![Testes](https://github.com/alisonvmarques/baliza/actions/workflows/testes.yml/badge.svg)](https://github.com/alisonvmarques/baliza/actions/workflows/testes.yml)

Sistema desktop e offline para conferir as contas dos fornecedores e em quais contas da entidade estão cadastradas antes de pagar.

> Em desenvolvimento. Versão atual: 0.3 · Entidade.

## O que o Baliza faz

- Guarda as contas bancárias e as chaves Pix de cada fornecedor.
- Registra em quais contas da entidade cada conta e chave Pix está cadastrada como favorecido.
- Na hora de pagar, mostra onde o fornecedor está cadastrado e avisa quando uma conta não está.
- Funciona totalmente offline, com os dados num arquivo criptografado ([como](docs/criptografia.md)).

## Desenvolvimento

Requer Python 3.11 ou mais novo.

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                           # testes
ruff check . && ruff format --check .   # verificação do código
baliza                           # abre o sistema
```

Os testes rodam no GitHub Actions em Windows, Linux e macOS a cada envio.

## Licença

[MIT](LICENSE) © 2026 Alison Vasconcelos Marques.
