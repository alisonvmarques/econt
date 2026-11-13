# ECont

[![Testes](https://github.com/alisonvmarques/econt/actions/workflows/testes.yml/badge.svg)](https://github.com/alisonvmarques/econt/actions/workflows/testes.yml)

Sistema desktop e offline que cuida das contas e das atividades da entidade: confere as
contas dos fornecedores e em quais contas da entidade estão cadastradas antes de pagar, e
acompanha num quadro o que o setor financeiro tem a fazer.

> Versão atual: 1.0 · Versão estável.

![Consulta de um fornecedor](docs/imagens/consulta-resultado.png)

## Para quem é

Para o setor financeiro de entidades que pagam fornecedores por mais de uma conta bancária.
No banco, cada conta da entidade
tem a sua lista de favorecidos: o pagamento só sai para quem está cadastrado naquela conta. O
ECont registra essa situação e mostra, antes de pagar, de quais contas o pagamento pode sair.

## O que o ECont faz

- Guarda as contas bancárias e as chaves Pix de cada fornecedor, conferindo CNPJ, CPF,
  agência, conta e chave.
- Registra em quais contas da entidade cada conta e chave está cadastrada como favorecido.
- Na Consulta, mostra o fornecedor com a situação em cada conta da entidade e avisa quando uma
  conta ou chave não está cadastrada em nenhuma.
- Imprime os dados para pagamento em meia folha A4, para anexar ao processo.
- Acompanha os limites diários de Pix e de transação de cada conta da entidade, com a regra de
  24 horas para alterações.
- Organiza as atividades da entidade num quadro (a fazer, em andamento, concluído), com
  prazos, fornecedor ligado e aviso no Início do que está atrasado ou vence hoje.
- Funciona totalmente offline, com os dados num arquivo criptografado
  ([como](docs/criptografia.md)), backup automático e exportação para pendrive.

## Instalação

No Ubuntu, no Linux Mint e no Debian, o ECont se instala pelo repositório de pacotes dele e
recebe as versões novas pelo Atualizador de software. Nos outros sistemas, baixe o instalador
na página de [versões](https://github.com/alisonvmarques/econt/releases):

| Sistema | Como instalar |
|---|---|
| Ubuntu, Linux Mint e Debian | Pelo repositório de pacotes: atualiza junto com o sistema |
| Windows 10 ou 11 | `ECont-<versão>-Windows-instalador.exe` |
| macOS | `ECont-<versão>-macOS.dmg` |
| Outras distribuições Linux | `ECont-<versão>-Linux-x86_64.AppImage` |

O passo a passo de cada sistema, inclusive os avisos de segurança na primeira vez, está em
[Instalação](docs/instalacao.md).

## Como usar

O [guia de uso](docs/index.md) explica cada área, com capturas de tela:

- [Primeiros passos](docs/primeiros-passos.md): senha, chave de recuperação e entidade.
- [Início](docs/inicio.md), [Consulta](docs/consulta.md), [Fornecedores](docs/fornecedores.md),
  [Entidade](docs/entidade.md), [Atividades](docs/atividades.md) e
  [Configurações](docs/configuracoes.md).
- [Perguntas frequentes](docs/perguntas-frequentes.md).

| Início | Marcações do fornecedor |
|---|---|
| ![Início](docs/imagens/inicio.png) | ![Marcações](docs/imagens/fornecedor-cadastros.png) |

Todas as capturas usam dados fictícios.

## Desenvolvimento

Requer Python 3.11 ou mais novo.

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                           # testes
ruff check . && ruff format --check .   # verificação do código
econt                           # abre o sistema
```

Os testes rodam no GitHub Actions em Windows, Linux e macOS a cada envio. Veja
[como contribuir](CONTRIBUTING.md).

## Licença

[MIT](LICENSE) © 2026 Alison Vasconcelos Marques.
