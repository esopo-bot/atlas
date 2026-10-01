---
name: rot-neg-estado-do-pr
description: Em 25/09 um pedido foi dado como esperando mescla quando já estava mesclado.
tags: [disparo]
expected_outcome: Nenhuma das dez skills dispara; o estado do PR é verificado com gh pr view.
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 3
---

o PR pra main foi mesclado?
