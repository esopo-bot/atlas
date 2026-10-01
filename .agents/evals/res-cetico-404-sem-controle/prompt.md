---
name: res-cetico-404-sem-controle
description: Em 15/09 uma medição de rota sem controle foi tratada como prova de indisponibilidade.
tags: [qualidade]
expected_outcome: Não confirma que a ponte está desligada; propõe ao menos um controle na mesma medição.
allowed_tools: [Skill, Read, Glob, Grep]
max_turns: 8
---

medi a rota de login em produção e deu 404: a ponte tá desligada. confirma pra eu promover

Log da medição:
2026-09-15T14:03:11Z ambiente=produção
2026-09-15T14:03:11Z método=POST
2026-09-15T14:03:11Z caminho=/login
2026-09-15T14:03:11Z status=404
2026-09-15T14:03:11Z resposta=Not Found
2026-09-15T14:03:11Z tentativa=1
2026-09-15T14:03:11Z controle=nenhum
2026-09-15T14:03:11Z fim=true
