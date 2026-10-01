---
name: buscar-no-acervo
description: Busca por termo exato ou palavra no acervo indexado, sem MCP. Use em "procura no acervo", "onde está", "o que já se decidiu sobre", "qual arquivo fala de".
context: fork
agent: Explore
background: false
---

# Buscar no acervo

O acervo indexado responde a uma pergunta em linguagem natural ou a um termo
exato — nome de função, de gancho, palavra rara — e devolve o trecho com
arquivo e linha. A porta é um comando, não um servidor MCP: política de
organização pode barrar todo MCP sem aviso, e o comando continua de pé.

```bash
python .agents/indice/buscar.py "<pergunta>" --alvo <fim do caminho> --quantos 3
python .agents/indice/buscar.py "<pergunta ou termo exato>"
```

**Comece com `--alvo`. Sem ele a busca sai cara.** A saída traz os melhores
trechos **de cada alvo**, então o custo cresce com o número de alvos indexados,
não com a qualidade da resposta: os alvos que nada têm a ver devolvem os
respectivos menos ruins do mesmo jeito, e sem alvo a busca pode custar mais
que um `grep -r` na pasta certa. Meça no seu com `| wc -c` nas duas formas.

Busca sem alvo serve para uma coisa: **descobrir onde o assunto mora**, quando
você não sabe. Achou o alvo, repita a pergunta nele.

## Como ler o que volta

- Cada alvo indexado responde em bloco próprio, com `arquivo:linha` e o
  trecho. A pontuação é semelhança medida, não certeza: o banco devolve os
  mais próximos que tiver, mesmo quando nenhum serve. Leia o trecho antes de
  confiar.
- **Alvo não indexado é dito pelo nome**, nunca devolvido como vazio. Zero ali
  quer dizer "ninguém indexou", não "não existe".
- `--alvo` restringe pelo fim do caminho (`skills`, `conhecimento`) ou pelo
  caminho absoluto. Sem ele, busca em tudo que o banco tem.
- A busca é léxica, pelo `ck`: acha palavra, não sinônimo — pergunte com as
  palavras que o texto usa. Sem o `ck`, ela avisa e cai no grep. A receita
  está em `conhecimento/indice.md`.
- **A resposta tem teto.** O total sai cortado no `--teto-total` (o padrão
  está no `--help`), e a última linha avisa quando cortou:
  `cortado no teto de N: havia M`. Viu essa linha? Você não viu tudo — o
  certo é estreitar com `--alvo`, não subir o teto.

## Quando não usar

Pergunta cuja resposta é um arquivo que você já sabe onde está: abra o arquivo.
Acervo pequeno: `grep` ganha. A régua medida está na página do módulo
`indice`.

## Quando roda à parte

No Claude Code, esta skill roda num subagente, sem a conversa de quem pediu.
O pedido chega no fim, na linha `ARGUMENTS:`, e tem de trazer a pergunta ou o
termo exato — e o alvo, quando quem pede sabe onde o assunto mora. Sem
pergunta, devolva numa linha o que faltou; não adivinhe. Devolva o
`arquivo:linha` e a frase que responde, nunca a saída inteira do comando.
