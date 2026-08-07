# Subagentes: um ajudante por tarefa

Subagente é um agente que o agente principal chama para uma tarefa fechada:
vasculhar o código, planejar, revisar. Ele trabalha à parte, com contexto
próprio, e devolve só a conclusão — o principal segue leve, sem carregar as
quarenta leituras que a busca custou.

## Quando vale a pena

- **Busca larga.** Responder "onde mora o cálculo de frete?" pode custar dezenas
  de arquivos lidos. No subagente, esse custo morre com ele.
- **Trabalhos independentes em paralelo.** Dois assuntos que não se tocam, dois
  subagentes ao mesmo tempo.
- **Papel fixo com regra própria.** Um revisor que sempre olha as mesmas coisas,
  descrito uma vez num arquivo.

O corte: subagente serve para **tarefa com começo e fim**, não para conversa. O
que precisa de ida e volta com você fica com o principal.

## Onde cada ferramenta guarda

O conceito é o mesmo em toda ferramenta; muda o endereço e o formato do
arquivo.

|         | Claude Code       | Devin                                  |
| ------- | ----------------- | -------------------------------------- |
| Pasta   | `.claude/agents/` | `.devin/agents/` ou `.agents/agents/`  |
| Formato | markdown          | markdown                               |
| Prontos | Explore, Plan     | `subagent_explore`, `subagent_general` |

Só entram aqui os endereços conferidos numa máquina. Outra ferramenta que
você use provavelmente tem o seu — procure na documentação dela antes de
supor que é igual.

Um arquivo por subagente, com nome, descrição e a instrução do papel. A
descrição importa como na skill: é por ela que o principal decide quando chamar.

No Devin há um atalho a mais: uma skill vira subagente pelo frontmatter —
`subagent: true`, ou `agent: <perfil>` para rodar com um perfil pronto. É
recurso experimental: pode mudar de forma.

## Um exemplo, no formato do Claude Code

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

A linha `tools` é a coleira: um revisor só lê. Sem ela, o subagente herda as
ferramentas todas — inclusive as de escrever.

## A armadilha de onde abrir

Subagente mora junto das skills e obedece à mesma regra medida no
[mapa do repositório](mapa-do-repositorio.md): **carrega da raiz, nunca de uma
subpasta**. Sessão aberta no lugar errado roda sem nenhum deles, em silêncio.
