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

Só endereços conferidos numa máquina; outra ferramenta, procure na doc
dela. No Devin, skill vira subagente pelo frontmatter (`subagent: true`) —
recurso experimental.

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
