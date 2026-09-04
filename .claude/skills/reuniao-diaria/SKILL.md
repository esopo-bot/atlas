---
name: reuniao-diaria
description: Reunião diária de 30 minutos entre o dono e a sessão — abre com o que mudou, tira impedimentos, decide o pacote da noite e fecha com minuta escrita no quadro. Use quando pedirem a daily, a reunião do dia, o planejamento da noite ou "o que entra hoje". Escopo — A REUNIÃO. Executar o pacote é do executor de roteiros, pela trabalho-por-issue; colher o que a sessão ensinou é da encerramento-de-sessao. Palavras que a acordam — "vamos fazer a daily", "reunião do dia", "o que roda hoje à noite".
---

# Reunião diária

Trinta minutos, com hora de acabar. A reunião é conversa; o que fica dela é a
**minuta**, escrita no quadro. Sem minuta não houve reunião.

Se a casa tiver voz, a sessão fala a abertura e cada pergunta — e escreve
tudo, porque o texto é a minuta. O dono responde como quiser, inclusive só
por texto. A voz é da casa, não da camada: o comando mora onde a casa guarda
os scripts dela, e o dono o informa uma vez, no arquivo de instruções de
usuário dele.

## Antes de falar, meça

Tudo por instrumento, nada de cabeça, e o resultado cabe em cinco linhas.
Despejar a saída dos comandos é o erro caro desta etapa.

- **Projetos.** A lista única é o campo `projetos` de `nucleo/executor.json`
  — não existe outra. Ativo hoje é o que se moveu: commit nos últimos sete
  dias no repositório dele (`git -C projetos/<repositorio> log
  --since='7 days ago' --oneline`) ou linha aberta no quadro com a etiqueta
  dele. Os demais ficam calados.
- **O que espera pelo dono.** Cartão parado nele, sempre com o link — ele
  decide do celular.
- **A última minuta.** O comentário mais recente do quadro que começa por
  "Minuta": o que ficou combinado é o ponto de partida, não a memória.
- **Os dois contadores da semana, lado a lado.** Entregas vistas por quem
  recebe (PR mesclado nos últimos sete dias em cada repositório de projeto)
  e mudanças na camada (`git log --since='7 days ago' --oneline | wc -l` na
  raiz da camada). A camada é meio; o termômetro é a entrega. Os dois lado a
  lado é o que impede a ferramenta de virar o trabalho.

## A pauta, nesta ordem

1. **Abertura, 5 min.** As cinco linhas da medição. A sessão diz a hora de
   acabar.
2. **Impedimentos, 5 min.** O que trava o dono. Uma pergunta por vez, e a
   resposta vira linha no quadro ou item com link para ele — nunca fica só na
   conversa.
3. **O que entra, 15 min.** Para cada candidato, três perguntas, sempre as
   mesmas: *o que quem recebe vê no fim?* — *qual a menor mudança que prova a
   hipótese?* — *qual verificação diz que está pronto?* Candidato sem as três
   respostas não entra hoje.
4. **Fechamento, 5 min.** A minuta, lida e gravada.

A sessão avisa na metade do tempo e no fim. O dono estende dizendo; sem isso,
acabou.

## O pacote da noite

Cada item que entra é uma issue com as três respostas escritas, no repositório
que `nucleo/configuracao.json` declara — a receita é a skill
`trabalho-por-issue`. O pacote são esses números, na minuta. Disparar o
executor de roteiros é o passo seguinte e é decisão do dono na reunião.

Nada roda sozinho. Reunião pulada é fila parada, e está certo assim: a
próxima parte da última minuta.

## Onde já há quem decida

Onde a casa tem quem prioriza e quem lidera a técnica, a reunião é a
preparação do dono: a sessão é o par sênior que traduz o pedido recebido nas
três respostas, e a minuta é o que ele leva.

## A minuta

Comentário novo no quadro, pelo instrumento que já existe:
`python3 .agents/caixa/caixa.py relatar --corpo "..."`. Até quinze linhas:

- Minuta de <data>
- Impedimentos: um por linha, cada um com o destino que ganhou
- Entra hoje: uma linha por issue, com a verificação que diz pronto
- Espera pelo dono: o link
- Contadores da semana: entregas vistas × mudanças na camada
- A correção do dia: uma linha — o que o dono pediu de um jeito caro e como
  sairia mais barato. É o item 4 da `encerramento-de-sessao`, em uma linha,
  todo dia.
- Próxima reunião: quando

## Pedidos de exemplo

- "vamos fazer a daily"
- "reunião do dia: o que entra hoje à noite?"
- "abre a reunião, tenho trinta minutos"
