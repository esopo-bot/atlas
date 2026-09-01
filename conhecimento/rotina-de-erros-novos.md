# A rotina que abre issue só para erro novo

Uma rotina que varre o log, agrupa o que é o mesmo erro e abre issue **só
para o que ainda não tem issue**. Ela não conserta nada sozinha: propõe, e
quem aprova é gente.

**O log não viaja; o mecanismo, sim.** Onde o seu log mora, como se busca
nele e quais são as assinaturas do seu sistema é do seu workspace. O que
está escrito aqui é a ordem dos passos, que vale em qualquer lugar.

## O mecanismo, em ordem

### 1. Varra a janela de retenção

Toda ferramenta de log tem uma janela: passado dela, o dado não existe mais.
Antes de varrer, saiba qual é a sua, e peça um período que caiba dentro
dela.

A retenção é **parte da prova**, não detalhe de configuração: fora da
janela, "não achei" quer dizer "não sei" — nunca "não aconteceu". Quem
ensina isso é [investigação de incidente](investigacao-de-incidente.md), na
seção das armadilhas de medição. Está escrito lá, e esta página não repete.

### 2. Agrupe por assinatura

Assinatura é o que faz duas ocorrências serem o mesmo erro. Monta-se com as
partes estáveis — o tipo da falha e o ponto do código onde ela nasceu — e
sem as que mudam a cada ocorrência: identificador, horário, valor de campo,
quem chamou.

O ajuste da assinatura é o trabalho todo:

- **larga demais** junta erros diferentes numa issue só, e a correção de um
  deixa o outro vivo, agora escondido atrás de uma issue fechada;
- **estreita demais** abre uma issue por ocorrência, e o quadro vira ruído
  em uma semana.

O sinal de que está boa: a mesma falha, em dias diferentes, cai no mesmo
grupo.

### 3. Compare com as assinaturas já conhecidas

A lista do que já se conhece mora em arquivo, não na memória da rodada —
rotina que roda sozinha não lembra de ontem (regra 4).

Conhecida é a assinatura que já tem issue, **aberta ou fechada**. As duas
contam, por motivos diferentes:

- com issue **aberta**, não se abre nada: no máximo um comentário com a
  contagem nova;
- com issue **fechada** e voltando a aparecer, é regressão — reabre-se a
  issue antiga, com o número na mão. Abrir uma nova joga fora tudo que já
  se descobriu ali.

### 4. Abra issue só para o que é novo

Vira issue só o que sobrou dos dois filtros. Cada uma leva o que quem for
consertar precisa ter na mão:

- a assinatura, e uma ocorrência inteira como exemplo;
- **a janela varrida e a contagem dentro dela** — escopo medido é o que
  separa o erro de uma pessoa do erro de todo mundo;
- o instante da primeira ocorrência vista, com o aviso de que a janela pode
  ter cortado o começo.

### 5. Proponha a correção em branch

Uma branch por issue, com a correção e o teste que falha sem ela. A rotina
que só abre issue já paga por si; a que também propõe a correção encurta o
caminho — desde que pare no lugar certo, que é o passo seguinte.

### 6. Nunca mescle sozinha

**Isto é parte da receita, não nota de rodapé.** A rotina roda sem ninguém
olhando, sobre um agrupamento que ela mesma inventou, propondo uma correção
que ninguém leu. Mesclar nessas três condições é publicar sem revisão.

O limite: ela abre a issue, empurra a branch e — onde o repositório
autorizar — abre o pedido de incorporação. E para. Quem aprova e mescla é
gente. É a regra 9, e ela não muda porque a rotina acertou nas dez vezes
anteriores.

## Como saber se ela está funcionando

Os dois modos de falhar são silenciosos:

- **abriu issue demais** — a assinatura está estreita, ou a lista do que já
  se conhece não está sendo lida. O sintoma é issue repetida no quadro.
- **não abriu nenhuma** — pode ser que não houve erro novo, e pode ser que a
  varredura quebrou. Zero só vira prova com contraprova: na mesma rodada, a
  mesma busca tem de achar alguma coisa — o total de erros do período, por
  exemplo. Sem isso, o que se registra é "não medido", nunca "nenhum erro
  novo".

## O que fica no seu workspace

Aqui está a receita; a montagem é sua, e não viaja:

- onde o log mora e como se busca nele;
- as regras de assinatura do seu sistema;
- onde a lista das assinaturas conhecidas fica gravada;
- em que repositório as issues nascem, e com que etiqueta;
- de quanto em quanto tempo a rotina roda.
