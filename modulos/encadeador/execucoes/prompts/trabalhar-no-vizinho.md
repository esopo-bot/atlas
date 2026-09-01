# Trabalhar no repositório vizinho

Faça o trabalho desta issue DENTRO do repositório alvo, na branch que a etapa anterior abriu lá. O alvo está na variável de ambiente PROJETO, e a sua sessão NÃO começa dentro dele: rode git como `git -C "$PROJETO" ...` e escreva nos caminhos sob `$PROJETO`. O que fazer está no corpo da issue: leia o prompt refinado e siga por ele.

O ALVO É A FRONTEIRA: escrever fora de `$PROJETO` é reprovação, não descuido — a etapa seguinte mede a árvore do workspace e para se ela ficar suja. A camada NÃO se instala no alvo: nada de copiar `.agents/`, `conhecimento/` ou `nucleo/` para lá. O alvo é um repositório de código, e continua sendo depois que você sair.

O QUE VOCÊ NÃO PODE FAZER NESTA ETAPA: empurrar, abrir pedido de incorporação, mesclar em branch de longa duração. A fronteira é DE ETAPA, não de sempre: quem mescla na integração do alvo, empurra e abre o pedido de incorporação da integração para a branch de publicação é a RODADA, depois da auditoria — mesclar a branch de publicação e publicar seguem do dono, sempre. COMMITE O QUE FIZER, no alvo e na branch de trabalho, antes de fechar a sua evidência: a etapa seguinte para se a árvore do alvo ficar suja, e evidência que diz `segue` sem commit não entrega nada.

O CRITÉRIO DE PARADA: só feche a sua evidência quando os critérios de aceitação estiverem cumpridos, ou quando o orçamento de turnos acabar. Evidência que diz `segue` com uma lista de faltas e orçamento sobrando é trabalho abandonado, não entrega — e quem retoma paga de novo o contexto que você já tinha. Falta que você não conseguiu cumprir se declara com a MEDIÇÃO que te barrou, nunca como item de lista sem porquê.

A PROVA: cada afirmação da sua evidência tem comando e saída, e o comando precisa re-executar a partir da raiz do workspace — use `git -C "$PROJETO" ...`, nunca um caminho de máquina escrito à mão. Teste ANTES de dar por pronto — o teste que não falha quando o código quebra não é teste. O CÓDIGO SEGUE AS REGRAS DE QUALIDADE injetadas na abertura (grandes autores; comentário explicativo é sinal de nome errado — o porquê mora na issue, nunca no código). Revise o seu diff contra elas antes de commitar.
