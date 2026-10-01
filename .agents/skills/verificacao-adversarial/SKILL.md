---
name: verificacao-adversarial
description: Verificação adversarial antes de agir — separa provado de suposto, desenha a medição mais barata que derrubaria cada suposição, executa o que dá, e reemite o veredito em provado/provável/não provado. Duas formas — atacar uma conclusão, ou revisar um corpo de código por várias lentes, com céticos derrubando cada achado. Use ao fechar conclusão ou investigação, antes de escalar, antes de aplicar correção baseada em hipótese, ao auditar um módulo por vários ângulos, ou quando pedirem para desafiar ou refutar. Fim de sessão é da encerramento-de-sessao. Palavras que a acordam — "roda o cético nisso", "desafia essa conclusão", "isso está mesmo provado?", "revisa esse código por várias lentes".
---

# Cético

Conclusão não atacada não está pronta — ataque antes que a realidade o faça.

## O procedimento

1. **Desmonte a conclusão em afirmações.** Escreva as afirmações estruturais
   — aquelas que, se falsas, derrubam o veredito. Ignore as decorativas.
2. **Marque cada uma: provada ou suposta.** Provada = existe saída de
   instrumento que você viu. "É assim que costuma ser", "o código sugere" e
   "faz sentido" são suposições, mesmo quando corretas.
3. **Para cada suposta, desenhe a medição mais barata que a derrubaria.** A
   pergunta não é "como confirmo?" — é **"o que eu veria se ela fosse
   falsa?"**. Confirmação encontra o que procura; refutação encontra o que
   existe.
3.1. **Zero e vazio não provam ausência.** "Não achei" é resultado de
   instrumento, não fato sobre o mundo: pode ser retenção vencida, filtro
   estreito, ou o próprio instrumento sem cobertura ali. Antes de aceitar um
   zero como conclusão, exija a contraprova positiva — o mesmo instrumento
   achando algo que você **sabe** que está lá. Sem essa contraprova, o zero
   vira "não medido", nunca "não existe".
4. **Execute o que der.** Medição barata primeiro. O que não puder ser medido
   agora fica registrado como não medido — não como verdade provisória.
5. **Reemita o veredito em três faixas:** provado (instrumento mostrou),
   provável (evidência forte, sem instrumento), não provado (segue de pé por
   falta de contradição). Liste ao fim o que continua sem prova.

## A regra de ouro

**A hipótese se anuncia com o mesmo volume de voz da evidência, nunca mais
alto.** Se três medições sustentam a conclusão e uma peça é suposição, isso
se diz na mesma frase — não numa nota de rodapé que ninguém lê.

## Sinais de que a conclusão precisa do cético agora

- Ela apareceu cedo e tudo depois pareceu confirmá-la.
- Ela é a única hipótese que alguém levantou.
- Ela explica o sintoma sem explicar o **começo** dele ("por que hoje?").
- Alguém vai agir caro em cima dela — escalar, reverter — ou ela vai sair
  do workspace: e-mail, pedido de revisão, mensagem a terceiro.

## O desenho antes do código

Em mudança de cerca, gancho ou política, o cético lê o **desenho** antes da
primeira linha de código: onde mora a declaração que liga a peça, quem fica
isento e por quê, e o que acontece num clone, numa worktree, numa sessão sem
ninguém no terminal e com outro agente. Furo de desenho achado depois do
código custa a rodada inteira, porque o código, os casos e os mutantes se
refazem. Achado antes, custa um parágrafo.

## Quando o alvo é o trabalho de outra sessão

A verificação vale mais numa sessão **limpa**, que não tem apego à conclusão.
Três travas a mais:

- **Rode os instrumentos você mesmo.** Saída colada por outra sessão é
  citação, não prova: ela mostra que alguém rodou algum dia, não que passa
  agora — e quem escreveu o texto é o menos indicado para dizer se ele está
  certo.
- **Não conserte nada.** Quem verifica e arruma no meio do caminho
  devolve mais mudança não revisada, e você perde justamente o par de
  olhos independente que foi buscar. Isto é um relatório.
- **Se a afirmação for um número, meça de novo e diga o que você contou.**
  Número é o achado mais fácil de "refutar" por engano: duas medições honestas
  de coisas ligeiramente diferentes discordam, e a discordância parece erro
  quando é definição.
- **Conserto de um conserto se compara em três pontos**: a base, a ponta
  anterior e a nova. Contra a base só, o diff soma os dois consertos e
  esconde a regressão que o segundo abriu sobre o primeiro.

## A segunda forma: várias lentes sobre um corpo de código

A primeira forma ataca uma conclusão. A segunda audita um corpo de código
inteiro: as lentes acham, e cada achado vira uma conclusão que os céticos
atacam pelo procedimento acima.

- **Lentes independentes.** Cada lente olha por um ângulo só e não vê o que
  a outra achou. A **lente do usuário final é obrigatória**: ela refaz a
  conta que o usuário veria, com os números reais do dado, nunca com
  exemplo inventado.
- **Vários céticos por achado, e a maioria derruba.** Cada cético tenta
  refutar sozinho; o achado cai quando a maioria o refuta.
- **Céticos por achado só nos graves**, e um deles de outra família de
  modelo: famílias diferentes erram em lugares diferentes. O achado menor
  vai ao relato com o veredito da lente só, dito assim.
- **O custo se declara antes de rodar**: lentes mais céticos, contra o
  `teto_de_agentes_por_sessao` de `nucleo/configuracao.json`. A forma cheia
  passa do teto com facilidade, e o teto não sobe por conta própria.
- **Achado sem voto não é achado refutado.** Quando o teto acaba antes dos
  céticos, o achado fica sem voto, e o relato separa as duas listas:
  refutado foi medido; sem voto não foi.

### O primeiro cético é o `codex review`

Quando o alvo é uma mudança num repositório e o despacho ao Codex existe e
diz ligado, a rodada abre com a revisão do Codex, antes de qualquer cético
em Claude: é a outra família de modelo, e custa minutos. Sem o despacho —
outra instalação, o espelho público — o passo não existe, e a rodada começa
nas lentes.

```bash
python .agents/despacho/despacho.py --estado
python <raiz do atlas>/.agents/despacho/despacho.py --revisar \
  --base <integração>
```

- Rode o `--revisar` da raiz da árvore revisada, com o caminho por extenso
  do `despacho.py`: a revisão roda da pasta atual e não aceita `-C`.
- O parecer sai em JSON: `saida` é o arquivo do `-o`, e `gasto_de_cota` é
  a diferença da cota lida antes e depois, porque o `turn.completed` chega
  zerado.
- A resposta mora no arquivo do `-o`. Depois de `Full review comments:` —
  ou `Review comment:`, quando o achado é um só —, um item por achado:
  `- [P<n>] <título> — <arquivo>:<início>-<fim>`, com a explicação nas
  linhas de baixo. P0 e P1 são graves. O `--output-schema` não muda esse
  formato.
- Os achados do Codex são a primeira lista de achados, não veredito: os
  céticos em Claude tentam derrubá-los como a qualquer outro. Zero achado
  não dispensa as lentes (passo 3.1).

### A rodada em Claude é o workflow `ceticos`

No Claude Code, as lentes e os céticos rodam pelo workflow salvo
`.claude/workflows/ceticos.js`, chamado como `/ceticos`, com estes `args`:

- `alvo`: `{"base": "<integração>", "ponta": "HEAD"}`, ou
  `{"arquivos": ["<caminho>"]}`;
- `revisao_do_codex`: o texto do arquivo do `-o`, quando o passo acima
  rodou;
- `contexto`: o que a mudança diz fazer, na frase do objetivo da issue.

As lentes, o teto de agentes da rodada e quem ganha um segundo cético moram
no script, não aqui. Ele devolve as listas provado, provável, não provado,
derrubado e sem voto, cada achado com o comando e a saída de quem votou.
Leia antes `lentes_que_cairam` e `revisao_do_codex.fora_do_formato`: o que
está ali ficou sem medir. Com `nao_mediu`, todas as lentes caíram e não há
lista: rode de novo, porque zero lido não é zero achado.
Rode de novo o comando do achado em que vai agir, e leve o veredito ao corpo
da issue. Agente sem workflow faz a rodada à mão, pelas regras desta seção.

## Comando destrutivo se julga pela cerca

Verificador mandado em somente leitura não roda comando destrutivo para
provar o furo de uma cerca: nem empurrão forçado, nem branch apagada, nem
história reescrita. O furo se prova sem o dano:

- **Julgue o comando só pela cerca.** Entregue a ela, na entrada padrão, a
  mesma entrada que ela recebe do cliente, e leia o veredito que devolve.
  Passou ou recusou é a prova.
- **Se precisar ver o shell rodar**, ponha um `git` falso na frente do
  `PATH`, que só anota o que recebeu, e rode num repositório sem remoto. O
  que o shell executaria fica escrito, e nada sai da máquina.

## O que isto não é

Não é revisão de código nem verificação de implementação — para isso, use
as rotinas de revisão da sua ferramenta. Aqui o alvo é o **raciocínio**: a
ponte entre o que foi medido e o que foi concluído. Na segunda forma o código
é só o terreno: o que se julga continua sendo cada achado.
