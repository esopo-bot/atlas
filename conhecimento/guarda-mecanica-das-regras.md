# A guarda mecânica de cada regra

Regra que só vive em prosa depende de alguém ler sob cansaço — e é sob
cansaço que se lê errado. Esta página diz, regra a regra, **o que a cobra na
prática**: o gancho que recusa na hora, a rotina que reprova no ritual, ou
nada.

A lista das regras é `regras-da-camada.md`. Aqui não se repete o que elas
dizem; só quem as segura.

## Como esta página se refaz

Ela é medição, não opinião. Para verificar se ainda está certa:

```bash
for h in .claude/hooks/*.py; do
  printf '%-34s ' "$(basename "$h" .py)"
  grep -oE '[Rr]egra [0-9]+' "$h" | sort -u | tr '\n' ' '; echo
done
python3 .agents/camada/camada.py medir provar
```

O primeiro comando diz qual gancho cita qual regra; o segundo prova os
ganchos e os instrumentos — e é o que viaja. No atlas, o catálogo inteiro das
rotinas sai por `python3 verificacoes.py --lista`, que não viaja. Divergiu desta tabela, esta página é que está velha.

## O quadro

| Regra | Quem a cobra | Como |
| --- | --- | --- |
| 1 — abra a sessão na raiz | nada | não mecanizável aqui: quem abre no lugar errado não tem a camada carregada para ser avisado |
| 2 — só é pronto o que um instrumento provou | rotina `verificacao` do motor | acusa veredito `segue` com `provado` vazio, e re-executa cada prova declarada |
| 3 — antes de criar, procure e cite | nada | **só prosa** |
| 4 — a memória mora no disco | as dez recusas dos ganchos | nenhuma rotina reprova, mas **toda recusa manda gravar** o aprendizado em `conhecimento/`, com a linha concreta do que gravar — memória previne, gancho ensina |
| 5 — ao dar por pronto, faça a análise de promoção | nada | **só prosa** |
| 6 — trabalhe econômico | rotina `largada` | cobra o teto de bytes que toda sessão paga, declarado em `nucleo/configuracao.json` |
| 7 — rede com cortesia | nada | **só prosa** |
| 8 — segredo não entra em git nenhum | gancho `orientar-credencial`; rotina `ensaio` | o gancho intercepta leitura e shell; o ensaio varre texto, caminho e mensagem de commit antes de publicar |
| 9 — destrutivo é do dono; commit e push | ganchos `vetar-branch-protegida`, `vetar-pergunta-ja-respondida`, `vetar-escrita-em-somente-leitura`, `vetar-comentario-explicativo` e `vetar-escrita-em-politica` | os dois primeiros leem `autorizacoes` e, sem declaração, negam; o terceiro recusa escrita em território de outra pessoa; o quarto recusa o agente editar a lista de exceções da própria cerca; o quinto recusa, durante etapa do executor, escrita nos arquivos que decidem quais cercas existem — `settings.json`, as listas que os ganchos leem, `nucleo/regras.json` e o código dos próprios ganchos |
| 10 — texto na régua | rotina `camada` | roda o validador de markdown sobre todo `.md` que o git rastreia |
| 11 — não invente passo onde já existe receita | nada | **só prosa** |
| 12 — branch de longa duração e integração contínua | ganchos `vetar-branch-protegida` e `vetar-automacao` | recusam na hora, pelo nome da branch e pelo caminho da configuração |
| 13 — publicar exige revisão semântica | rotina `ensaio`, **em parte** | a varredura acha nome e segredo; jeito de trabalhar e procedência não têm padrão e passam inteiros. A parte que falta **não é mecanizável** |
| 14 — conhecimento nasce na língua de quem vai lê-lo | rotina `vocabulario`; ganchos `vetar-conhecimento-em-codigo` e `vetar-comentario-explicativo` | a rotina mede o fechamento de cada termo na árvore rastreada e acusa saldo; os ganchos recusam a página nascendo em pasta de código e o porquê nascendo em comentário |
| 15 — editou a fonte, regenere a cópia | gancho `vetar-escrita-em-copia-gerada`; rotina `sincronia` | o gancho recusa a escrita na cópia nomeando a fonte; a rotina regenera e compara o texto inteiro |
| 16 — nada sem destino | ganchos `cobrar-destino-da-entrega` e `vetar-escrita-fora-da-execucao`; rotinas `entrega` e `higiene` | o primeiro cobra na parada da sessão; o segundo recusa escrita fora da raiz da execução, que não entra em commit nenhum; a rotina `entrega` lista o que não saiu da branch, e a `higiene` varre o rastreador pelos termos do assunto — issue que fala do trabalho e não aponta para a que o consolidou, e texto que descreve como aberta uma issue já fechada. As três primeiras guardas olham para o disco e para o git; nenhuma via o rastreador, e era ali que a issue vizinha ficava para trás |
| 17 — explique na altura de quem lê | nada | **não mecanizável**: altura de explicação não se mede por padrão |

## O que este quadro ensina

**Seis regras não têm guarda nenhuma** — 1, 3, 5, 7, 11 e 17. Duas delas
(1 e 17) não são mecanizáveis pelo que são; as outras quatro são
candidatas, e a candidata mais barata é sempre a que já tem instrumento e
não tem quem o chame.

**A regra 4 saiu da lista sem ganhar rotina.** Nada reprova a sessão que
não grava. O que mudou é que toda recusa passou a mandar gravar, com a
linha pronta: memória previne, gancho ensina. Guarda por prompt é mais
fraca que guarda por rotina, e o quadro diz isso em vez de fingir o
contrário.

**Guarda mecânica não é tudo.** A classe de erro que nenhum gancho pega é
outra: **interpretar errado um texto lido corretamente**. Foi o que aconteceu
quando uma regra geral atropelou um procedimento específico e nada acusou o
conflito — as duas frases estavam certas, e a leitura é que escolheu a errada.
Para essa classe a trava é revisão adversarial, não gancho: alguém, ou alguma
etapa, pergunta *por que não o contrário?* antes de a decisão virar ação.

**Nada fica sem destino.** A cobrança da regra 16 é sobre a branch de
entrega **e** o passo seguinte: ou o trabalho vai para lá com o pedido de
incorporação ABERTO, ou é descartado com a razão dita em uma linha.
Trabalho parado antes disso não chegou a lugar nenhum, só parece pronto —
mesmo que o commit já esteja na branch certa.

**A cobrança pode nomear um PR que já fechou.** O gancho lê o estado local
sem `git fetch` antes — se o dono mesclou o pedido de incorporação segundos
antes de a sessão encerrar, a lista de commits que ele imprime já está
resolvida no GitHub. Confira com `gh pr view <número> --json state` e
`git fetch origin && git log --oneline origin/main..origin/homolog` antes de
abrir um PR novo: `state: MERGED` e 0 commits de diferença fecham o caso sem
nenhuma ação — não é um alarme falso do gancho, é uma corrida entre a
mesclagem e a leitura.
