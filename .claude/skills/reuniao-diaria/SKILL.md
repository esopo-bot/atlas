---
name: reuniao-diaria
description: Reunião diária de 30 minutos entre o dono e a sessão — abre com o que mudou, tira impedimentos, decide o pacote da noite e fecha com minuta escrita no quadro. Use quando pedirem a daily, a reunião do dia, o planejamento da noite ou "o que entra hoje". Escopo — A REUNIÃO. Executar o pacote é do executor de roteiros, pela trabalho-por-issue; colher o que a sessão ensinou é da encerramento-de-sessao. Palavras que a acordam — "vamos fazer a daily", "reunião do dia", "o que roda hoje à noite".
---

# Reunião diária

Trinta minutos é a régua, não o gatilho de parada: **a reunião fecha quando o
plano do dia existe.** Passou da hora sem plano, ela continua; saiu o plano
antes, ela acaba antes. A reunião é conversa; o que fica dela é a
**minuta**, escrita no quadro. Sem minuta não houve reunião.

Se o repositório tiver voz, a sessão fala a abertura e cada pergunta — e escreve
tudo, porque o texto é a minuta. O dono responde como quiser, inclusive só
por texto. A voz é do repositório, não da camada: o comando mora onde o repositório guarda
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
- **Os canais onde o dono já conversa — onde ele abrir, e só.** Caixa de
  entrada e mensageiro do trabalho, filtrados pelos assuntos que estão
  abertos. **Espera de terceiro morre no canal onde foi feita:** o quadro só
  sabe o que alguém digitou nele, e resposta que chegou por mensagem não
  vira linha sozinha. Cada achado vira comentário na issue correspondente na
  hora, com a data em que a resposta chegou — nunca fica só na conversa;
  nome de pessoa de fora não atravessa para issue pública. **Onde a leitura
  não couber — política da empresa, volume, canal corporativo —, quem filtra
  é o dono:** ele traz o recorte na abertura e a sessão não vai atrás. Não é
  perda; é a mesma fonte com outro portador. A minuta registra qual dos dois
  caminhos valeu no dia.
- **Os dois contadores da semana, lado a lado.** Entregas vistas por quem
  recebe (PR mesclado nos últimos sete dias em cada repositório de projeto)
  e mudanças na camada. **A camada não se conta pelo total do `git log`:**
  esse número infla sozinho, porque artefato gerado obriga a regravar o
  mesmo arquivo a cada parada, e mesclagem conta como trabalho sem ser.
  Conte os commits que **não** revisitam arquivo já tocado na mesma semana:
  é o que separa construção de retrabalho. A camada é meio; o termômetro é a
  entrega. Os dois lado a lado é o que impede a ferramenta de virar o
  trabalho.

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

A sessão avisa na metade do tempo e quando a régua estoura — avisar não é
encerrar. **Sem plano do dia não há fechamento**, e o aviso vira uma pergunta:
o que falta decidir para termos o plano? O dono encurta dizendo; a sessão, não.

## O pacote da noite

Cada item que entra é uma issue com as três respostas escritas, no repositório
que `nucleo/configuracao.json` declara — a receita é a skill
`trabalho-por-issue`. O pacote são esses números, na minuta. Disparar o
executor de roteiros é o passo seguinte e é decisão do dono na reunião.

Nada roda sozinho. Reunião pulada é fila parada, e está certo assim: a
próxima parte da última minuta.

## Onde já há quem decida

Onde o repositório tem quem prioriza e quem lidera a técnica, a reunião é a
preparação do dono: a sessão é o par sênior que traduz o pedido recebido nas
três respostas, e a minuta é o que ele leva.

## A minuta

Comentário novo no quadro, pelo instrumento que já existe:
`python .agents/caixa/caixa.py relatar --corpo "..."`. Até quinze linhas:

- Minuta de `<data>`
- Impedimentos: um por linha, cada um com o destino que ganhou
- Entra hoje: uma linha por issue, com a verificação que diz pronto
- Espera pelo dono: o link
- Contadores da semana: entregas vistas × mudanças na camada
- A correção do dia: uma linha — o que o dono pediu de um jeito caro e como
  sairia mais barato. É o item 4 da `encerramento-de-sessao`, em uma linha,
  todo dia.
- Próxima reunião: quando

Ensaie antes de gravar, com `--ensaio`: o instrumento avisa palavra com
dígito colado a letra, o erro mais comum de quem escreve número no meio da
frase. Corrija e só então grave. Depois de gravar, releia o comentário no
quadro: só é minuta o que está lá como você escreveu — regra 2.

## Pedidos de exemplo

- "vamos fazer a daily"
- "reunião do dia: o que entra hoje à noite?"
- "abre a reunião, tenho trinta minutos"
