# Moldes do trabalho por issue

Os moldes que a abertura usa. O corpo da skill diz quando abrir cada um.

## Bloco de perfil do passo zero

O bloco que se grava no perfil do repositório, em `conhecimento/projetos/`.
Os nomes são os que o repositório usa, nunca os que a skill imagina:

Onde as issues moram, o padrão de nome e o fluxo do backlog **não entram
aqui**: têm lugar próprio, o `nucleo/configuracao.json` — um fato, um
lugar. Este bloco guarda o resto:

```markdown
## Trabalho por issue

- **Quadro de acompanhamento:** <como o repositório o chama, e onde ele fica>
- **Estados do quadro, na ordem:** <os nomes de lá>
- **Rótulos que importam:** <quais, e o que cada um significa aqui>
- **Etapas de verificação:** <como o repositório chama cada uma, e o que prova
  cada>
- **Branch onde a sessão trabalha:** <o padrão do nome, e de qual branch nasce>
- **Branch de entrega, e o que o nome dela aciona:** <integração contínua?
  implantação? aviso a outras pessoas?>
- **A sessão pode empurrar:** <o que sim, e o que só o dono empurra>
- **Branches protegidas** — não apagar, não renomear, não forçar, não
  reescrever: <os nomes das de longa duração. Na dúvida, é protegida.>
- **Quem encerra a issue:** <o papel, nunca o nome de uma pessoa>
- **Onde moram os procedimentos:** <a documentação de como se sobe, publica e
  libera acesso — é aqui que se procura antes de inventar passo>
```

A última linha é a que mais rende: gravada uma vez, ela faz a próxima sessão
achar a receita em vez de improvisar uma.

## Molde do corpo da issue

```markdown
## Objetivo
<uma frase: o que muda no mundo quando isto fechar>

## Escopo
Dentro: <lista curta>
Fora: <o que esta issue explicitamente não resolve>

## Critério de aceitação
- [ ] <verificável por comando ou observação — nunca por opinião>
- [ ] <...>

## Onde mexer
<caminhos e módulos. "Ainda desconhecido" é resposta válida e útil.>

## Estado
Fase: investigar | implementar | verificar
Feito: <...>
Parcial: <o que está pela metade, e onde parou>
Falta: <...>
Decisões: <uma linha cada, com link para o comentário que decidiu>

## Ponto de retomada
<o bloco da seção "Virar a sessão" da skill, reescrito a cada virada>
```

## Molde da issue para sessão sem cabeça

As cinco seções que se acrescentam **sobre** o molde de cima, quando quem vai
executar é uma sessão sem ninguém por perto. Elas existem porque essa sessão
não pode perguntar nada: o que não estiver aqui, ela inventa ou trava.

```markdown
## O pedido, como veio
> <o texto do dono, VERBATIM — sem corrigir, resumir ou melhorar>

## O prompt para a sessão
<autossuficiente, escrito para quem não leu a conversa: o que ler antes, o
que fazer e em que ordem, o que provar, e o que não tocar. Endereço de
arquivo por NOME (função, seção); número de linha só como dica datada.>

## Onde rodar
Diretório: <o caminho do alvo, e por que é esse>
Como disparar: <o comando literal>

## Branch e trabalho em andamento
Conflita? <sim | não> — <o que a medição mostrou>
Branches recentes no mesmo assunto: <...>
Alvos paralelos: <o que `git worktree list` respondeu, e em que commit>
PRs abertos sobre a base: <número e título, ou "nenhum">

## Commit de partida
<o SHA, nunca `HEAD` nem nome de branch — os dois envelhecem entre a
declaração e a execução (regra 2)>
```

O par que faz isto valer: **pedido original e prompt refinado juntos**. O
primeiro é a âncora do que foi pedido; o segundo, o que a entrevista fechou.
Sozinho, o refinado vira a interpretação de alguém, e ninguém consegue
verificar se ela é fiel.

## Exemplos de critério de aceitação

O teste da skill: o critério começa pelo instrumento ou pelo adjetivo?

| Não serve                       | Serve                                                       |
| ------------------------------- | ------------------------------------------------------------ |
| "o login está funcionando bem"  | "`<comando de teste>` passa, incluindo o caso de senha errada" |
| "o código foi revisado"         | "a revisão apontou N achados e todos estão resolvidos ou respondidos" |
| "ficou mais rápido"             | "a mesma chamada, medida do mesmo jeito, cai de X para menos de Y" |
| "medir cinco vezes antes e depois" | "mediana de 5 rodadas antes e 5 depois, ~N s por conjunto; a etapa que mede declara `tempo-limite` no roteiro acima do padrão de 3600 s" |
| "documentado"                   | "a página `<caminho>` existe e um estranho executa o passo a passo dela" |

## Molde da issue de pergunta

Para quando a decisão é do dono, e a sessão não pode chutar. Pergunta curta,
opções medidas — nunca imaginadas —, recomendação e o porquê em uma linha:

```markdown
## A pergunta
<a pergunta em UMA linha, respondível escolhendo uma opção>

## O estado de hoje, medido
<o que existe no disco, com arquivo:linha e o comando que provou>

## As opções
### <nome> — <o que muda>
Custo: <medido, com o comando>
O que se perde: <o preço real de escolher esta>

### <nome> — ...
(no máximo três opções; cada uma com o custo medido, nunca estimado)

## A recomendação
<qual opção, e o porquê em uma frase que um júnior entende>
```

Duas ou três opções, cada uma com número que veio de comando — não de palpite.
Quando a pergunta some outra decisão dentro de si (por exemplo, "isto depende
de outra issue"), diga isso em uma linha ligada, sem misturar as duas escolhas
no mesmo corpo.

O título leva o prefixo `<projeto>_pergunta -`, e a etiqueta `parado-em-voce` —
é ela que faz a coluna do quadro mostrar que a issue espera o dono, e que o
executor de roteiros não a dispare sozinho.

## Molde do quadro fixo

Para o trabalho que não acaba: um projeto que segue vivo, uma caixa de entrada,
um território que acumula defeito. A issue **não fecha** — ela enche e esvazia.
O corpo é o estado de hoje; os comentários são o log de cada movimento.

Cinco seções, nesta ordem:

```markdown
# O quadro de <o trabalho> — o que ainda falta

**Esta issue não fecha.** Ela é a orquestradora: enche com pendências, esvazia
quando cada uma resolve, e guarda o estado entre sessões. Toda sessão que for
trabalhar aqui começa lendo o corpo desta issue.

## Onde o trabalho mora
<o repositório, a pasta, o remoto e o que cada um autoriza. É o endereço que a
sessão nova precisa antes de tocar em qualquer coisa.>

## Regras deste trabalho
<as ordens que valem sempre, uma por linha: o que não se publica, com quem não
se fala, o que nunca entra nesta issue.>

## Pendências
<uma linha por assunto, cada uma com dono e data — formato abaixo.>

## Vencidos
<a régua escrita, e o que ela pega hoje. Quase sempre vazia: é assim que se
sabe que alguém a está lendo.>

## Ponto de retomada
<o bloco da seção "Virar a sessão" da skill.>
```

Uma linha por **assunto**, não por evento: o mesmo problema que chegou por três
caminhos é uma linha só.

### A linha de pendência: dono e data

```markdown
- [ ] `<dono>` · desde <dd/mm> — <a pendência em uma frase, com o endereço da prova>
```

Linha sem dono é linha órfã: todo mundo lê e ninguém pega. Linha sem data não
envelhece — some do radar sem nunca vencer.

O **dono** é quem dá o próximo passo, nunca quem pediu. Três bastam, e é o
repositório que os nomeia, no perfil do passo zero: o que só o responsável pode
fazer, o que é trabalho de sessão, e o que espera resposta de fora.

A **data** é a de quando a linha passou às mãos do dono da vez — nunca a de
hoje. Carimbar a data de hoje ao arrumar o quadro zera o relógio de todas as
linhas de uma vez, e o quadro passa a parecer novo para sempre.

Linha resolvida não some: vira `[x]` riscada com o que a fechou, ou sai por
poda registrada em comentário.

### A régua de vencimento

`Vencidos` não é lista que alguém mantém à mão: é a régua escrita, e o que ela
pega no dia em que foi verificada.

```markdown
## Vencidos

Linha de pendência parada além da régua, medida pela data da própria linha:

| Dono da vez | Vence em |
| --- | --- |
| <trabalho de sessão> | mais de <n> dias |
| <decisão do responsável> | mais de <n> dias |
| <resposta de fora> | mais de <n> dias |

**Nenhuma hoje** — verificado em <data>.
```

Os prazos são **do repositório**, não da skill: espera por gente de fora aguenta
mais que trabalho parado na própria mão, e quanto mais, cada repositório
decide. Sem
prazo declarado não há vencido — e quadro que nunca acusa vencido não é lido
duas vezes.

**"Esperando resposta de fora" só vale com pedido registrado.** Se ninguém
consegue dizer a data em que alguém pediu, a linha não espera terceiro: ela
espera a gente pedir. Chamar de bloqueio externo o que é tarefa nossa parada é
a issue mentindo para a próxima sessão — e é a mentira mais cara, porque
ninguém cobra quem está esperando.
