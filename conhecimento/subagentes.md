# Subagentes: um ajudante por tarefa

Subagente é um agente que o principal chama para tarefa fechada: vasculhar,
planejar, revisar. Trabalha à parte e devolve só a conclusão.

## Quando vale

| Caso | Por quê |
| --- | --- |
| busca larga | as quarenta leituras morrem com ele |
| trabalhos independentes em paralelo | dois assuntos, dois subagentes |
| papel fixo com regra própria | um revisor descrito uma vez, num arquivo |

O corte: tarefa com começo e fim. Conversa fica com o principal.

## Onde cada ferramenta guarda

|         | Claude Code       | Devin                                  |
| ------- | ----------------- | -------------------------------------- |
| Pasta   | `.claude/agents/` | `.devin/agents/` ou `.agents/agents/`  |
| Formato | markdown          | markdown                               |
| Prontos | Explore, Plan     | `subagent_explore`, `subagent_general` |

Só endereços verificados numa máquina; outra ferramenta, procure na doc
dela. No Devin, skill vira subagente pelo frontmatter (`subagent: true`) —
recurso experimental.

## O que a camada traz: `varredor`

Um só, e de leitura pura (`Read, Grep, Glob`). Ele responde pergunta fechada
sobre o repositório inteiro — *onde ainda aparece X*, *quantos Y existem* — e
devolve conclusão com `caminho:linha`, nunca o despejo.

**Por que ele não duplica o `Explore` do fabricante:** o `Explore` acha código.
O `varredor` carrega as regras desta camada — devolve número no lugar de
adjetivo, separa o total bruto do saldo aberto quando há exceção declarada, e
não escreve "não existe" sem antes provar que a busca sabe achar (regra 2).
Ele também **não roda comando**: devolve o comando que reproduz cada número,
para quem o chamou rodar. É assim que a coleira fica curta e o número vira
prova.

O caso que o justifica: varredura larga come a janela da sessão que está
trabalhando, e é por isso que inventário e renomeação grande nunca começam.

## Exemplo, no formato do Claude Code

`.claude/agents/revisor.md`:

```markdown
---
name: revisor
description: Revisa mudanças procurando bug e escopo ampliado.
tools: Read, Grep, Glob
---

Revise o que mudou. Para cada achado: arquivo:linha, por que é problema e o
caso concreto que quebra. Sem caso concreto, não é achado.
```

- A linha `tools` é a coleira: sem ela, o subagente herda tudo — inclusive
  escrever.
- A descrição decide quando o principal o chama, como na skill.
- Subagente carrega da raiz, nunca de subpasta — mesma regra do
  [mapa](mapa-do-repositorio.md#onde-abrir-o-agente).
