# Mexida em repositório vizinho

Este roteiro faz o trabalho de uma issue **dentro de outro repositório do
seu workspace**, sem instalar a camada nele. O alvo é um repositório de
código, e continua sendo depois que a execução sai.

A configuração continua sendo lida da **raiz do workspace**; o que muda é
onde o `git` roda. O alvo chega por variável de ambiente:

```sh
PROJETO=<caminho-do-repositorio-alvo> ISSUE=<n> ASSUNTO=<assunto-em-kebab> \
  python3 .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/mexida-em-vizinho.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias
```

## As três recusas, e o porquê de cada uma

O primeiro estágio é a barreira. Ele recusa antes de tocar em qualquer
coisa, e a mensagem diz o motivo — recusa muda que não se explica vira
tentativa de adivinhar de novo.

| Quando | Por que recusa |
| --- | --- |
| `PROJETO` não veio | adivinhar alvo é escrever no lugar errado |
| o alvo não tem `.git` | só sabe trabalhar dentro de um repositório |
| o alvo é somente leitura | dele se lê, nele não se escreve |

**A lista de somente leitura não mora no roteiro.** Ela sai de
`nucleo/executor.json`: cada projeto se declara em `projetos.<etiqueta>`, e o
que tem `somente_leitura: true` entra na lista pelo nome do `repositorio`. O
gancho `.claude/hooks/vetar-escrita-em-somente-leitura.py` deriva a lista da
MESMA chave — por isso a recusa vale por qualquer caminho, não só por este
roteiro. Fato repetido em dois lugares envelhece torto e passa a mentir de um
dos lados, e é por isso que os dois leem o mesmo campo.

O molde está em `nucleo/executor.exemplo.json`, que viaja com a camada.

## Os cinco estágios

| Estágio | O que prova |
| --- | --- |
| `abrir-branch-no-vizinho` | a branch nasceu no alvo, no commit da base |
| `trabalhar` | a sessão faz o pedido da issue, dentro do alvo |
| `trabalho-commitado` | alvo limpo, commit novo, nada mexido fora |
| `trabalho-empurrado` | a branch chegou ao repositório durável do alvo |
| `verificacao` | as provas dos estágios re-executam e batem |

Toda prova roda a partir da raiz do workspace e chega ao alvo por
`git -C "$PROJETO" ...`. É isso que deixa a verificação re-executar:
caminho de máquina escrito à mão morre na primeira máquina diferente.

A prova de commit novo ancora no **SHA** da base, não em `origin/<base>`.
Ref que anda envelhece a prova antes de a verificação chegar nela.

## Empurrar no alvo, sem empurrar cego

Commit que fica só na árvore do alvo não existe para o resto do mundo, e
some no dia em que aquela pasta sumir — é a regra 16. Por isso o estágio
`trabalho-empurrado` leva a branch de trabalho ao repositório durável do
alvo e prova o destino comparando o `rev-parse HEAD` do alvo com o
`ls-remote --heads origin` dele. Sha diferente é trabalho que não chegou;
remoto que não respondeu é **não medido**, nunca "chegou".

Cego ele não empurra. Antes, procura a etiqueta do alvo — o nome da
pasta de `PROJETO` em `projetos.<etiqueta>.repositorio` — e para
quando a resposta do cadastro é não:

| Quando | O que ele diz |
| --- | --- |
| o alvo não tem etiqueta declarada | falta `projetos.<etiqueta>.repositorio` com o nome da pasta |
| o cadastro diz `somente_leitura` | o caminho é pedido de incorporação como sugestão, com o `revisor` declarado |
| `autorizacoes.push` não está ligado | omissão não é permissão: ligue a chave, ou peça ao dono |

As três leem a MESMA chave que os ganchos leem — o de somente leitura e o
de branch protegida. Empurrar cego bateria na cerca e pararia a execução
com um erro que não ensina nada.

## O que ele NÃO faz

- Não abre pedido de incorporação, e não mescla. Publicar é do dono.
- Não empurra onde o cadastro do alvo não autoriza.
- Não escreve fora do alvo — e isso é medido, não pedido: se a árvore do
  workspace ficar suja, `trabalho-commitado` reprova.
- Não instala a camada no alvo. Nada de `.agents/`, `conhecimento/` ou
  `nucleo/` copiados para lá.

## O que sai da configuração, e nunca do roteiro

| No roteiro | De onde vem |
| --- | --- |
| a base da branch de trabalho | `branches.base`, na raiz |
| o nome da branch | `branches.padrao_de_trabalho`, na raiz |
| quais repositórios são somente leitura | `projetos.<etiqueta>.somente_leitura` |
| se a automação pode empurrar no alvo | `projetos.<etiqueta>.autorizacoes.push` |
| a quem sugerir o pedido de incorporação | `projetos.<etiqueta>.revisor` |
| o repositório alvo | a variável `PROJETO` |
| o número da issue e o assunto | as variáveis `ISSUE` e `ASSUNTO` |

Troque a configuração e o mesmo roteiro serve outro workspace — é esse o
teste de que ele é mecanismo, e não o processo de alguém.
