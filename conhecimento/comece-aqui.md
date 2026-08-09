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
| Skills (`.agents/skills/`) | listadas no [canivete](skills-da-camada.md) — uma delas entra sozinha, por gancho |
| O guia (estas páginas)     | o prompt de partida e o saber de bolso                                                                               |
| O site (`site/`)           | o guia navegável — como construir está no `README.md` da raiz                                                           |

## Como usar o guia

- **Toda sessão começa e termina igual**: o prompt de partida e o esfriamento
  estão em [abrir e fechar a sessão](../fluxos/abrir-e-fechar-a-sessao.md) — a
  página seguinte a esta. A partida evita a sessão que varre tudo antes de
  perguntar; o esfriamento (uma linha: "Rode o esfriamento") colhe o que o
  dia ensinou antes de você fechar a janela.
- **Vai pedir automação, plugin ou skill?** Abra o
  [canivete](skills-da-camada.md) primeiro: metade do que você ia escrever já
  existe de fábrica.
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

## As três que doem se você não souber

Duas são regras da lista numerada em [regras da camada](regras-da-camada.md);
a terceira é uma fronteira do [mapa](mapa-do-repositorio.md). O **estrago de
ignorá-las** é o que ninguém descobre a tempo:

| Se você… | Acontece isto, e nada avisa |
| --- | --- |
| abrir a sessão numa subpasta | ela roda sem skill nenhuma — [regras da camada](regras-da-camada.md) |
| aceitar "terminei" sem ver a saída de um instrumento | você entrega o que ninguém mediu |
| dar nome de página da camada a um arquivo seu | a atualização o sobrescreve — o antídoto está no [mapa](mapa-do-repositorio.md) |

A atualização **nunca reescreve** o que é seu — instruções, suas skills, seus
arquivos. A fronteira exata está no [mapa](mapa-do-repositorio.md).
