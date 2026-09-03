# Prove que você lê a camada — antes de trabalhar

Prompt para QUALQUER agente de IA aberto na raiz de um repositório que
instalou a camada: cole inteiro e deixe o agente responder. Serve para o
agente de terminal, o assistente do editor e o Claude Code. O objetivo é um
só: o agente prova, com saída colada, que enxerga as instruções e as skills
que este repositório carrega — ou diz exatamente o que não enxerga.

## O que você faz, nesta ordem

1. **Liste as skills que você enxerga agora**, pelo nome, sem abrir pasta
   nenhuma. Depois rode `ls .agents/skills` e compare: o que está na pasta
   e não apareceu na sua lista é skill que você NÃO lê. Cole as duas listas.
2. **Responda sem abrir arquivo:** quais são as nove barreiras do portão da
   camada, na ordem? Só depois abra `.agents/skills/portao/SKILL.md` e
   confira. Acertou os nove nomes na ordem: você leu a skill. Inventou ou
   pulou: não leu. Diga qual foi.
3. **Responda sem abrir arquivo:** o que este repositório manda fazer antes
   de criar algo novo, e quem pode publicar? Depois abra `AGENTS.md` e
   confira. "Procurar e citar o que já existe" e "publicar é do dono" são as
   respostas que provam a leitura.
4. **Diga de onde você lê instrução e skill** — o nome exato dos arquivos e
   pastas que o seu runtime carrega neste repositório. Se você não sabe,
   diga "não sei", nunca chute.
5. **Repita 1 a 3 numa conversa nova**, porque uma medição não é medição: a
   escolha de skill varia entre conversas.

## O que você entrega

Uma tabela, colada num comentário da issue que pediu esta prova:

| passo | resultado | prova colada |
| --- | --- | --- |
| skills que enxergo | N de M da pasta | as duas listas |
| barreiras do portão | acertei / errei em ... | a resposta antes de abrir |
| ordem do AGENTS.md | acertei / errei em ... | a resposta antes de abrir |
| de onde leio | arquivos e pastas | a lista, ou "não sei" |
| repetição | igual / diferente em ... | a segunda rodada |

E um veredito em uma linha: **leio os dois**, **leio só as skills**, **leio só
o AGENTS.md** ou **não leio nenhum**. Onde não ler, o que faltou, com nome:
arquivo que o runtime não carrega, configuração que falta, política que barra.
Nada de suposição.

## O que você NÃO faz

Não instale nada, não mude configuração, não edite a camada. Se algo barrar,
isso é achado para o dono, com a mensagem exata — não conserto seu.
