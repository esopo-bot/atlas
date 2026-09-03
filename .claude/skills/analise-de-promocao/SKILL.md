---
name: analise-de-promocao
description: Use ao dar UM trabalho por pronto, quando pedirem a análise de promoção, ou quando perguntarem o que do trabalho atual pode virar genérico. O fechamento da sessão inteira é da skill encerramento-de-sessao, que chama esta.
---

# Análise de promoção

Esta análise decide, antes do resumo final, o destino do que a sessão criou.

## Antes das pilhas: a conclusão está auditada?

Se o trabalho terminou numa conclusão — uma causa encontrada, um diagnóstico,
uma regra deduzida —, passe o cético nela (skill `verificacao-adversarial`) antes de promover
o que quer que seja. Lição promovida sem auditoria vira regra que outras
pessoas seguem: o erro sai de um repositório e entra em todos.

## As três pilhas

Releia o que a sessão criou e aprendeu, e separe:

- **Genérico** — serviria a qualquer pessoa, em qualquer repositório.
- **Do workspace** — vale só para este.
- **Descartável** — morre com a sessão.

## O destino de cada pilha

- **Genérico**: proponha a promoção — o quê, para onde na camada (página,
  skill, gancho ou template) e o texto **já abstraído**: sem nome de pessoa,
  projeto, empresa ou máquina. **Proponha; não aplique** — promoção é decisão
  do dono, e camada pública não aceita resíduo pessoal.
- **Do workspace**: escreva como nota ou decisão em
  `conhecimento/<subpasta>/` — o lugar que o mapa do repositório reserva ao
  que é seu.
- **Descartável**: diga o que descartou, em uma linha — o dono pode discordar.

## O endereço se verifica, não se adivinha

Antes de propor para onde vai, **procure na camada a página que já trata do
assunto e cite-a**. Promoção que não verifica a página existente abre a
segunda versão do mesmo fato — e duas versões envelhecem torto, até uma delas
passar a mentir. Achou a página? A proposta é **melhorar aquela página**, não
abrir outra.

Não achou página nenhuma? A página nova só se propõe **com o endereço de
chegada junto** — o link vindo de uma página que já é lida. A regra está em
`conhecimento/mapa-do-repositorio.md` do repositório de origem da camada, em
"Página nova precisa de quem a leia":
conhecimento sem endereço não existe para quem precisa dele, e há rotina que
reprova página órfã.

## A régua da dúvida

Vale a regra 5 de `conhecimento/regras-da-camada.md`: na dúvida, é pessoal, e
fica no workspace. Deixar de promover se corrige amanhã; vazar não se
despublica.

## Pedidos de exemplo

- "acabei de fechar o ajuste do cache aqui, tem alguma coisa nele que serve pros outros repositórios?"
- "roda a análise de promoção nesse trabalho que eu acabei de terminar"
- "terminei a correção do parser de datas. o que dela vale a pena virar genérico?"
