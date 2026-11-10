# Revisão de qualidade da versão 1.0

Revisão feita antes da versão estável (issue #55), contra os requisitos não funcionais.
Cada item tem um teste automático que roda no GitHub Actions em Windows, Linux e macOS.

## RNF02 · Consulta em menos de 1 segundo

Base de teste com 5 contas da entidade e, para cada fornecedor, duas contas bancárias e uma
chave Pix, todas com marcações. Mediana de 20 medições, num computador comum:

| Fornecedores | Busca por nome | Busca por CNPJ | Resultado do fornecedor |
|---:|---:|---:|---:|
| 500 | 7 ms | 7 ms | menos de 1 ms |
| 2.000 | 29 ms | 26 ms | menos de 1 ms |

Com 2.000 fornecedores, quatro vezes o volume previsto, a busca fica cerca de 35 vezes
abaixo do limite. Teste: `tests/test_consulta.py::test_busca_em_menos_de_um_segundo_com_500_fornecedores`.

## RNF03 · Confirmação antes de excluir ou inativar

| Ação | Onde | Confirmação |
|---|---|---|
| Inativar fornecedor | Ficha do fornecedor | "Inativar este fornecedor?" |
| Excluir fornecedor (só sem histórico) | Ficha do fornecedor | "Excluir este fornecedor?" |
| Excluir conta ou chave Pix (só sem histórico) | Diálogo da conta ou da chave | "Excluir conta" / "Excluir chave" |
| Inativar conta ou chave Pix (com histórico) | Diálogo da conta ou da chave | "Inativar conta" / "Inativar chave" |
| Inativar conta da entidade | Entidade › Contas | "Inativar conta" |
| Marcar todas | Ficha › Cadastros | "Marcar todas as contas?" |
| Restaurar backup | Configurações › Backup | Diálogo "Substituir os dados atuais", com a senha ou a chave |
| Conta ou chave repetida em outro fornecedor | Diálogos de conta e chave | Aviso e segundo clique em "Salvar mesmo assim" |

Em toda confirmação, o botão padrão é Cancelar: Enter sem pensar não apaga nada. Reativar
não pede confirmação, porque não perde nada.

## RNF04 · Mensagens de erro

- Todas as mensagens estão em português e dizem o que corrigir, com um exemplo quando ajuda
  ("Informe a conta com o dígito depois do traço, assim: 77777-3.").
- Os erros de formulário aparecem no próprio campo, com borda e texto, nunca só pela cor.
- Erro inesperado (por exemplo, disco cheio na hora de gravar) não fecha o ECont sem
  explicação: aparece uma mensagem em português dizendo o que houve e que os dados gravados
  antes continuam no arquivo. Os detalhes técnicos ficam num botão, para quem precisar.

## RNF05 · Só pelo teclado

Fluxos percorridos sem o mouse, em `tests/test_teclado.py`:

- Entrar com a senha: Enter no campo da senha.
- Trocar de área: Ctrl+1 a Ctrl+5, ou Tab até a barra e as setas.
- Consulta: digitar, Enter abre o primeiro fornecedor, o foco vai para Imprimir meia folha,
  Esc limpa a busca e a seta para baixo leva à lista.
- Fornecedores: Enter na lista abre a ficha; no formulário, Enter em qualquer campo salva.
- Diálogos de conta, chave Pix, conta da entidade e banco: Enter salva, Esc cancela.
- Pedido de alteração de limite: Enter no novo valor registra o pedido.
- Marcações: Tab chega a cada caixa e Espaço marca ou desmarca.
- Abas da ficha e das Configurações: Ctrl+Tab passa para a próxima.

Encontrado e corrigido nesta revisão: nos formulários que ficam na própria página (novo
fornecedor, dados da entidade e pedido de limite), Enter não salvava; só os diálogos
salvavam com Enter.
