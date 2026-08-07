---
slug: /
---

# Comece aqui

Esta é a camada: instruções, fluxos e skills que qualquer agente de IA —
Claude Code, Codex, Devin — passa a seguir no repositório onde ela for
montada. Esta página diz o que ela instala, como usar o guia e o que a
atualização preserva. Duas leituras e você está pronto.

## O que a camada instala

| Peça                       | O que faz por você                                                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md` + `CLAUDE.md`  | as regras que todo agente lê ao abrir a sessão                                                                          |
| Skills (`.agents/skills/`) | listadas em [as skills da camada](skills-da-camada.md) — uma delas entra sozinha, por gancho |
| O guia (estas páginas)     | os templates de prompt e o saber de bolso                                                                               |
| O site (`site/`)           | o guia navegável — `cd site`, depois `npm install` e `npm run build`                                                    |

## Como usar o guia

- **Toda sessão começa e termina igual**: a partida e o esfriamento estão
  em [abrir e fechar a sessão](../fluxos/abrir-e-fechar-a-sessao.md) — a
  página seguinte a esta. A partida evita a sessão que varre tudo antes de
  perguntar; o esfriamento (uma linha: "Rode o esfriamento") colhe o que o
  dia ensinou antes de você fechar a janela.
- **Vai pedir outra coisa a um agente?** O resto dos
  [templates](../fluxos/templates.md) está por situação: pedido grande,
  entender código, bug, escalação, revisão.
- **Quer saber onde cada coisa mora e o que a atualização sobrescreve?**
  [Mapa do repositório](mapa-do-repositorio.md).
- **O que a sessão não muda sem você:** a lista numerada em
  [as regras da camada](regras-da-camada.md) — os prompts de partida e de
  fechamento mandam o agente lê-la.
- **Vai criar ou testar uma skill?** [Skills: criar e testar](skills-criar-e-testar.md).
- **Quebrou em produção?** [Investigação de incidente](../fluxos/investigacao-de-incidente.md)
  — e, se alguma busca devolver vazio, [zero que mente](zero-que-mente.md).
- O resto — [ganchos](ganchos.md),
  [plugins](plugins-oficiais-do-claude-code.md), [MCP](mcp.md),
  [subagentes](subagentes.md),
  [história em issue](../fluxos/historia-em-issue.md) — é consulta: abra
  quando o assunto aparecer.

## As três regras que não mudam

1. **Abra a sessão na raiz** — a pasta que tem o `AGENTS.md`. O que decide é
   **onde você abre**, não onde o arquivo mora; aberta numa subpasta, a sessão
   roda sem skill nenhuma e nada avisa.
2. **Só é pronto o que um instrumento provou.** Build, teste, listagem — "o
   modelo disse" não é prova.
3. **A atualização só toca o que veio da camada.** O que é seu — instruções,
   suas skills, seus arquivos — ninguém sobrescreve. A fronteira exata está no
   [mapa](mapa-do-repositorio.md).
