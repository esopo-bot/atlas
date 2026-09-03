---
name: verificacao-adversarial
description: Verificação adversarial de uma conclusão antes de agir sobre ela — separa provado de suposto, desenha a medição mais barata que derrubaria cada suposição, executa o que dá, e reemite o veredito em provado/provável/não provado. Use ao fechar conclusão ou investigação, antes de escalar, antes de aplicar correção baseada em hipótese, ou quando pedirem para desafiar ou refutar. Escopo — UMA conclusão. Fim de sessão é da encerramento-de-sessao. Palavras que a acordam — "roda o cético nisso", "desafia essa conclusão", "isso está mesmo provado?", "e se estiver errado?".
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

## O que isto não é

Não é revisão de código nem verificação de implementação — para isso, use
as rotinas de revisão da sua ferramenta. Aqui o alvo é o **raciocínio**: a
ponte entre o que foi medido e o que foi concluído.

## Pedidos de exemplo

- "concluí que o gargalo é o banco, porque a página só demora quando tem muita linha. antes de eu refatorar em cima disso, ataca essa conclusão"
- "acho que o teste tá quebrando por causa de fuso horário. me desafia nisso antes de eu sair mexendo"
- "roda o cético nisto: o erro só acontece em produção, então é problema de configuração"
