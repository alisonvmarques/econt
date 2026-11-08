# Atualizar a lista de bancos

O Baliza traz a lista oficial de participantes do Banco Central em
`src/baliza/dados/recursos/bancos.csv` (código COMPE, ISPB e nome). Ela é carregada na base de
dados na primeira abertura. Atualize a lista antes de cada nova versão.

1. Baixe a lista em <https://www.bcb.gov.br/estabilidadefinanceira/participantesstr>
   (arquivo `ParticipantesSTR.csv`).
2. Na pasta do projeto, rode:
   ```bash
   python scripts/atualizar_bancos.py caminho/para/ParticipantesSTR.csv
   ```
3. Atualize `DATA_DA_LISTA` em `src/baliza/dados/lista_bancos.py`.
4. Rode `pytest` e confira a diferença com `git diff --stat`.
5. Faça o commit: `Atualiza a lista de bancos do Banco Central (AAAA-MM-DD)`.

Instituições sem código COMPE ficam de fora: elas não recebem transferências por agência e conta.
Bancos cadastrados manualmente pelo usuário nunca são alterados pela lista oficial.
