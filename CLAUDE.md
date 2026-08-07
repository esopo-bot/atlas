# CLAUDE.md

As instruções deste repositório estão em:

@AGENTS.md

## O que é só do Claude Code

O que mora em cada pasta de `.claude/` está na árvore do
`conhecimento/mapa-do-repositorio.md`. Só três coisas não estão lá:

- `settings.local.json` é pessoal, criado automaticamente e fica fora do git.
- `skills/` é cópia gerada pelo `montar.py` e **entra no git** — sessão na
  nuvem só enxerga o que está commitado. Não se edita ali; edite em
  `.agents/skills/` e rode `python montar.py --sincronizar`.
- Pasta vazia guarda `.gitkeep`, nunca um `.md`: qualquer `.md` solto em
  `commands/` vira um comando de barra de verdade.
