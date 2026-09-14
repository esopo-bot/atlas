# CLAUDE.md

As instruções deste repositório estão em:

@AGENTS.md

Sessão nova: leia `.agents/prompts/bootstart.md` inteiro antes de atender o
pedido, seja ele qual for — é o briefing da camada. `/bootstart <pedido>`
faz essa leitura por você.

## O que é só do Claude Code

O que mora em `.claude/` está na árvore do
`conhecimento/mapa-do-repositorio.md`. Três exceções:

- `settings.local.json`: pessoal, criado automaticamente, fora do git.
- `skills/`: cópia gerada pelo `montar.py --sincronizar` e **entra no git**
  — sessão na nuvem só enxerga o commitado. Edite em `.agents/skills/`,
  nunca aqui.
- Pasta vazia guarda `.gitkeep`, nunca um `.md`: qualquer `.md` solto em
  `commands/` vira um comando de barra de verdade.
