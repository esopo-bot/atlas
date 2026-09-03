---
name: buscar-no-acervo
description: Busca por significado ou termo exato no acervo indexado, sem MCP. Use em "procura no acervo", "onde está", "o que já se decidiu sobre", "qual arquivo fala de".
---

# Buscar no acervo

O acervo indexado responde a uma pergunta em linguagem natural ou a um termo
exato — nome de função, de gancho, palavra rara — e devolve o trecho com
arquivo e linha. A porta é um comando, não um servidor MCP: política de
organização pode barrar todo MCP sem aviso, e o comando continua de pé.

```bash
python3 .agents/indice/buscar.py "<pergunta ou termo exato>"
python3 .agents/indice/buscar.py "<pergunta>" --alvo <fim do caminho> --quantos 3
```

## Como ler o que volta

- Cada alvo indexado responde em bloco próprio, com `arquivo:linha` e o
  trecho. A pontuação é semelhança medida, não certeza: o banco devolve os
  mais próximos que tiver, mesmo quando nenhum serve. Leia o trecho antes de
  confiar.
- **Alvo não indexado é dito pelo nome**, nunca devolvido como vazio. Zero ali
  quer dizer "ninguém indexou", não "não existe".
- `--alvo` restringe pelo fim do caminho (`skills`, `conhecimento`) ou pelo
  caminho absoluto. Sem ele, busca em tudo que o banco tem.
- A busca é híbrida: significado mais termo exato, fundidos. `--denso` roda só
  por significado, para comparar; `--medir` compara os dois no seu acervo.

## Quando não usar

Pergunta cuja resposta é um arquivo que você já sabe onde está: abra o arquivo.
Acervo pequeno, abaixo de uns dois mil arquivos: `grep` ganha. A régua medida
está na página do módulo `indice`.

## Pedidos de exemplo

- "procura no acervo onde a autenticação decide quem entra"
- "o que já se decidiu sobre a cópia gerada que diverge da fonte? busca no acervo"
- "qual arquivo fala do gancho vetar-andamento-em-arquivo?"
