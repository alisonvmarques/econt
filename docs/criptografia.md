# Como o arquivo de dados é criptografado

Decisão tomada em 08/11/2026 (requisito RNF12).

## Opções comparadas

| | SQLCipher | SQLite na memória + arquivo cifrado com `cryptography` |
|---|---|---|
| Como funciona | Versão do SQLite que cifra o banco página por página | O banco fica na memória; ao salvar, o conteúdo inteiro é cifrado com AES-256-GCM e gravado |
| Windows, Linux e macOS | Depende de pacotes binários de terceiros, nem sempre disponíveis para todos os sistemas e versões do Python | `cryptography` tem pacotes oficiais para os três sistemas |
| Instalador (PyInstaller) | Biblioteca nativa extra para empacotar e testar em cada sistema | Funciona sem configuração extra |
| Senha e chave de recuperação | Uma única chave por banco; a recuperação exigiria outra solução | Envelope: a mesma chave dos dados é guardada cifrada pela senha e pela chave de recuperação |
| Desempenho | Bom para bancos grandes | Suficiente: o Baliza guarda poucos milhares de registros |

## Escolha

**SQLite na memória + arquivo cifrado com a biblioteca `cryptography`.**

- Uma chave aleatória de 256 bits cifra os dados (AES-256-GCM, que também detecta qualquer alteração no arquivo).
- Essa chave é guardada no arquivo duas vezes: cifrada pela senha e cifrada pela chave de recuperação, cada uma passada pelo scrypt (n = 2¹⁵, r = 8, p = 1), que torna lenta a tentativa de adivinhar a senha.
- Trocar a senha ou gerar uma chave de recuperação nova não exige cifrar os dados de novo.
- A gravação é atômica: o arquivo novo só substitui o antigo depois de gravado por inteiro.

A chave de recuperação tem 24 caracteres (120 bits), sem as letras I e O e sem os números 0 e 1,
para não haver confusão ao copiar da folha impressa.

Código: `src/baliza/dados/cofre.py` e `src/baliza/dados/banco.py`.
