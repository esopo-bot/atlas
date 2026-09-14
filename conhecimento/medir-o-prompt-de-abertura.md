# Medir o prompt de abertura, em vez de opinar sobre ele

Prompt que a sessão lê ao abrir é a peça mais cara da camada: ela cobra
contexto de toda sessão de todo mundo, e ninguém sabe dizer se funciona. A
régua usual é a opinião de quem o escreveu, que é a pior régua possível —
quem escreve já sabe o que quis dizer.

Esta página é a receita medida de trocar opinião por nota. Ela nasceu de seis
rodadas sobre o próprio prompt de abertura desta camada, e o que está aqui é
o que sobreviveu à medição.

## A forma: uma bancada de três braços

Uma rodada é um teste cego, e tem cinco passos:

1. **A versão sob teste é um commit.** Escreva ou corrija o prompt, commite, e
   é esse commit que a rodada mede. Sem commit não há versão, e sem versão não
   há comparação.
2. **Monte árvores isoladas, uma por tipo de trabalho.** Cada uma nasce
   daquele commit; o repositório vizinho entra clonado de um espelho local,
   preso num commit onde o defeito ainda existe. Nada toca repositório de
   verdade: o cliente do rastreador é um dublê e o `push` cai no espelho.
3. **Abra uma sessão sem cabeça em cada árvore**, com o pedido escrito como a
   pessoa o digitaria, e nada mais. Os ganchos e as cercas do repositório
   valem lá dentro — provado: uma cerca recusou um comando numa sessão sem
   cabeça, com a mensagem inteira no transcrito.
4. **Meça por instrumento o que dá**, e só o resto por julgamento. Criou
   branch de trabalho? Bateu em cerca? Resolveu o problema pela prova
   declarada? Colou a saída? Empurrou? Isso o disco e o rastreador respondem.
   Falou a língua de quem lê, contou o que faltava, seguiu receita: isso pede
   juiz.
5. **Cada erro vira uma correção do prompt**, e a correção vira a versão
   seguinte.

**O que muda de uma rodada para a outra é só o prompt.** Mesmo problema, mesmo
commit, mesmo modelo. É isso que torna a diferença atribuível ao texto.

## Os problemas fixos: pequenos, reais e prováveis por comando

O problema de cada braço se escolhe por três propriedades, nesta ordem:

- **Existe de verdade no commit declarado.** Problema inventado mede a
  obediência da sessão, não o trabalho dela.
- **Cabe numa sessão** — poucas dezenas de linhas, sem depender de serviço
  externo, login ou dado de gente.
- **Tem um comando que diz sim ou não**, sem adjetivo: uma contagem que era
  quatro e passa a ser zero, uma suíte que passa. Critério que começa pelo
  adjetivo não serve.

Três armadilhas medidas, todas caras:

- **Problema que já foi resolvido na vida real contamina a rodada.** Uma
  sessão leu o rastreador, viu o trabalho mesclado em produção e parou antes
  de duplicar. A conduta estava certa e a medição, perdida. Prefira problema
  sem história pública, ou esconda essa história do dublê.
- **Problema que nasce vazio dá nota falsa.** A contagem inicial foi feita
  numa cópia atrasada do repositório; na ponta, o defeito já não existia. As
  sessões disseram "nada a trocar", estavam certas, e o instrumento as
  reprovou por quatro rodadas.
- **O dublê precisa de memória.** Um cliente falso que inventa identificador
  e esquece o que criou faz a sessão gastar turnos investigando um registro
  que não existe. Guarde o que ele cria e devolva na leitura seguinte.

## A régua: o que instrumento mede e o que juiz julga

Separe os dois na hora de escrever a régua, porque misturar produz nota que
ninguém consegue reproduzir.

**Instrumento mede fato do disco e do rastreador**, e a armadilha é olhar o
estado final. Um medidor que lia a branch no fim da sessão reprovou justamente
quem fez tudo certo: criou a branch, empurrou, mesclou e podou o rastro — e
terminou na branch de integração, com a branch de trabalho já apagada. Meça o
**ato**, não o resíduo: a criação da branch nos comandos, o trabalho chegando
ao espelho, o commit da ponta sendo mescla.

**Juiz julga o que não tem instrumento**: língua, ordem da explicação, receita
seguida. Use mais de uma lente, exija trecho literal como evidência, e ponha
um cético por achado — mede-se que a maioria dos achados de painel não
sobrevive a quem tenta derrubá-los.

**Juiz também erra, e a bancada é quem o corrige.** Duas vezes um painel
propôs frase que contrariava a regra declarada do repositório, e as duas foram
descartadas por isso. Quando o juiz e o contrato divergem, o contrato ganha.

## O achado que paga a bancada inteira

**Regra escrita não muda o jeito de falar; exemplo copiável muda.**

Foi medido assim: quatro rodadas seguidas acrescentaram frases de regra sobre
como escrever — a língua, a ordem, o tamanho da frase. O item de conversa
ficou parado em zero de três nas quatro. Na rodada seguinte, as mesmas
intenções entraram como **três moldes prontos** — a linha entre duas
ferramentas, a primeira resposta, a resposta final — e o item foi de zero para
três de três na primeira tentativa.

A leitura que sobra: para **mecânica** (o que rodar, em que ordem, o que não
fazer), regra funciona. Para **forma** (como escrever, como explicar), só
exemplo funciona.

E há um irmão desse achado, medido no mesmo laço: **prompt que ninguém abre
não corrige nada.** Nas duas primeiras rodadas o briefing estava pronto e só
uma sessão o leu, porque o ponteiro para ele morava no meio do arquivo de
instruções. Movido para a primeira seção, a leitura foi a três de três, e
junto com ela o primeiro comando da abertura. **Ponteiro no topo vale mais que
capítulo bem escrito no fim.**

## Quando vale a pena

Não vale para texto que uma pessoa lê uma vez. Vale para o texto que **toda
sessão paga**: o prompt de abertura, as instruções da raiz, a descrição de uma
skill. Ali, meio ponto de nota se multiplica por todas as sessões de todo
mundo, e a opinião de quem escreveu custa mais caro que a medição.

Conte o preço antes: cada rodada abre uma sessão por braço e cobra por elas.
Uma rodada de três braços fica na casa de alguns dólares e vinte minutos. Seis
rodadas cabem numa madrugada.

E lembre da regra que vale para toda medição desta camada: **uma medição não é
medição.** Diferença de poucos pontos entre duas rodadas é ruído; o que se lê
é o piso que mudou de categoria — um item que era zero de três e virou três de
três.
