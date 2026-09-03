---
name: padrao-de-codigo
description: O padrão de código deste repositório — KISS, YAGNI, Tidy First, teste em três atos, erro na fronteira, nome no lugar de comentário. Uma regra por caminho carrega este texto quando você toca código; cite-a pelo nome só fora disso. Palavras que a acordam — "o padrão de código daqui", "revisa pelo padrão".
---

# Qualidade de código — a base

- **KISS e YAGNI:** a solução mais simples que resolve. Nada "para o futuro"
  sem uso hoje, nem camada ou padrão que o projeto não tem.
- **Abstração só com 2+ usos reais.** Um uso = código direto; abstração
  errada se espalha, duplicação se junta depois.
- **Arrume antes de mudar (Tidy First), em commit separado** — limpeza
  misturada com comportamento faz diff que ninguém consegue revisar.
- **Teste em três atos (AAA):** um comportamento por teste, nome que conta a
  história. Teste que não falha quando o código quebra não é teste.
- **Instrumento tem `--testar` próprio:** a bandeira se lê **antes** de
  converter qualquer argumento, e o teste chama as funções do próprio
  arquivo — senão o `--testar` estoura no próprio nome.
- **Erro se trata na fronteira:** valide na entrada, falhe com mensagem útil,
  nunca engula exceção.
- **Engolir erro em volta de uma CONTA é mentira.** Em volta de um efeito
  colateral, `suppress` é tolerância; em volta de uma medição, ele
  transforma falha em número — e o zero que sai parece um fato. Falha vira
  "não medido", nunca zero. Vale também para código de saída: a
  ferramenta que sai 2 errou, e errar não é achar nada.
- **Nome diz o que é.** Se precisou de comentário para explicar, o nome está
  errado.
- **Menor diff coerente:** mudança se fatia em entregas que passam sozinhas.

## Pedidos de exemplo

- "vou escrever esse módulo agora, me lembra o padrão de código que vale aqui"
- "esse arquivo tá cheio de comentário explicando o que o código faz. revisa ele pelo padrão daqui"
- "posso deixar essa abstração pronta pra um caso que ainda não existe?"
