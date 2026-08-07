---
name: cetico
description: Verificação adversarial de uma conclusão antes de agir sobre ela - separa o que está provado do que foi suposto, desenha a medição mais barata que derrubaria cada suposição, executa o que dá, e reemite o veredito em provado/provável/não provado. Use ao fechar uma investigação, antes de escalar, antes de aplicar correção baseada em hipótese, ou quando pedirem para desafiar, refutar ou "rodar o cético" numa conclusão.
---

# Cético

Conclusão que ninguém atacou não está pronta: ela é a primeira história que
explicou os fatos, e a primeira história costuma estar incompleta. Esta skill
ataca a conclusão antes que a realidade o faça.

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
- Alguém vai agir caro em cima dela: escalar, reverter, avisar cliente.

## O que isto não é

Não é revisão de código nem verificação de implementação — para isso existem
os comandos de revisar e verificar. Aqui o alvo é o **raciocínio**: a ponte
entre o que foi medido e o que foi concluído.
