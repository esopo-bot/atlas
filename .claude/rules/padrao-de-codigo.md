---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.cs"
  - "**/*.java"
  - "**/*.go"
  - "**/*.rb"
  - "**/*.php"
  - "**/*.kt"
  - "**/*.rs"
  - "**/*.sh"
  - "**/*.sql"
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
- **Erro escondido ainda avisa.** Onde suprimir é legítimo — em volta de um
  efeito colateral —, esconder a EXCEÇÃO é uma coisa e parar de AVISAR é
  outra. O aviso sobrevive: uma linha dizendo o que falhou e o que se perdeu
  com isso. Cerca que emudece some em silêncio, e o verde passa a significar
  "ninguém olhou".
- **Peça de interface usa o componente do repositório.** Antes de escrever marcação
  e estilo novos, procure no próprio repositório o componente que já resolve
  aquilo — mensagem, aviso, card, estado vazio — e use-o; cor, ícone e
  espaçamento vêm do tema, nunca cravados no arquivo. **A suíte não vê isto:**
  ela passa igual com a peça fora do padrão, então "os testes estão verdes"
  não atesta apresentação. Régua do pronto para tela inclui abrir a tela.
- **Nome diz o que é.** Se precisou de comentário para explicar, o nome está
  errado.
- **Menor diff coerente:** mudança se fatia em entregas que passam sozinhas.
