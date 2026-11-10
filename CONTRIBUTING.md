# Como contribuir

Obrigado pelo interesse. O ECont é pequeno de propósito: um sistema offline, em português,
para conferir contas de fornecedores antes de pagar.

## Antes de começar

- Abra uma issue descrevendo o problema ou a ideia antes de um pull request grande.
- Nunca use dados reais em issues, testes, capturas de tela ou exemplos: só dados fictícios
  (os CNPJs e contas dos testes são inventados).
- O ECont não acessa a internet. Mudanças que mandem dados para fora do computador não
  serão aceitas.

## Preparar o ambiente

Requer Python 3.11 ou mais novo.

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Antes de enviar

```bash
ruff check . && ruff format --check .
pytest
```

Os testes rodam no GitHub Actions em Windows, Linux e macOS. Toda regra nova precisa de
teste. Telas são testadas sem janela visível (`QT_QPA_PLATFORM=offscreen`).

## Convenções

- Código, nomes, mensagens e documentação em português.
- Mensagens de erro dizem o que corrigir, com um exemplo quando ajuda.
- Toda ação que apaga ou inativa pede confirmação, com Cancelar como botão padrão.
- Commits pequenos, citando a issue no fim: `Busca por CPF sem pontuação (#12)`.

## Capturas de tela da documentação

```bash
QT_QPA_PLATFORM=offscreen python scripts/capturas.py
```

O script cria dados fictícios numa pasta temporária e grava as imagens em `docs/imagens`.

## Instaladores

`python scripts/empacotar.py` gera o instalador do sistema em que roda. Os três são gerados
e conferidos pelo GitHub Actions quando uma versão é criada.
