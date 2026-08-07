---
name: qualidade
description: Padrão de qualidade de código - KISS, YAGNI, Tidy First, teste em três atos, erro tratado na fronteira. Entra por gancho no início da sessão; cite pelo nome se o gancho não estiver ligado.
---

# Qualidade de código — a base

- **KISS e YAGNI:** a solução mais simples que resolve. Nada "para o futuro"
  sem uso hoje.
- **Abstração só com 2 ou mais usos reais.** Um uso = código direto. Abstração
  errada custa mais caro que duplicação: a duplicação se junta depois, a
  abstração errada se espalha.
- **Arrume antes de mudar (Tidy First):** se o terreno está torto, endireite
  num commit separado antes da mudança de comportamento. Misturar os dois faz
  um diff que ninguém consegue revisar — não dá para ver o que é limpeza e o
  que muda o que o sistema faz.
- **SOLID pragmático:** responsabilidade única por classe/módulo; dependa de
  interface onde o projeto já depende; não invente camada que o projeto não
  tem.
- **Teste em três atos (AAA):** arrange, act, assert — um comportamento por
  teste, nome que conta a história. Teste que não falha quando o código quebra
  não é teste.
- **Erro se trata na fronteira:** valide na entrada, falhe com mensagem útil,
  nunca engula exceção. Erro engolido vira defeito que aparece longe de onde
  nasceu.
- **Nome diz o que é.** Se precisou de comentário para explicar, o nome está
  errado.
- **Menor diff coerente.** Mudança grande se fatia em entregas pequenas que
  passam sozinhas.
- **Ao responder sobre código:** direto ao ponto, sem preâmbulo nem epílogo.
