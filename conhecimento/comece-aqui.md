---
slug: /
---

# Comece aqui

A camada: instruções, fluxos e skills que qualquer agente de IA — Claude
Code, Codex, Devin — passa a seguir no repositório onde ela for montada.

## O que a camada instala

| Peça                       | O que faz por você                                                          |
| -------------------------- | --------------------------------------------------------------------------- |
| `AGENTS.md` + `CLAUDE.md`  | as regras que todo agente lê ao abrir a sessão                              |
| Skills (`.agents/skills/`) | listadas no [canivete](skills-da-camada.md) — uma entra sozinha, por gancho |
| O guia (estas páginas)     | o prompt de partida e o saber de bolso                                      |
| O site (`site/`)           | o guia navegável — construção no `README.md` da raiz                        |

## Onde ir

| Você quer                            | Abra                                                                       |
| ------------------------------------ | -------------------------------------------------------------------------- |
| Abrir e fechar o dia                 | [abrir e fechar a sessão](../fluxos/abrir-e-fechar-a-sessao.md)            |
| Pedir automação, plugin ou skill     | [canivete](skills-da-camada.md) — metade já existe de fábrica              |
| Saber onde cada coisa mora           | [mapa do repositório](mapa-do-repositorio.md)                              |
| O que a sessão não muda sem você     | [as regras da camada](regras-da-camada.md)                                 |
| Criar ou testar uma skill            | [skills: criar e testar](skills-criar-e-testar.md)                         |
| Investigar quebra em produção        | [investigação de incidente](../fluxos/investigacao-de-incidente.md)        |
| Entender uma busca que devolveu zero | [zero que mente](zero-que-mente.md)                                        |

Consulta, quando o assunto aparecer: [ganchos](ganchos.md) ·
[plugins](plugins-oficiais-do-claude-code.md) · [MCP](mcp.md) ·
[subagentes](subagentes.md) ·
[história em issue](../fluxos/historia-em-issue.md).

## As três que doem

| Se você…                                            | Acontece isto, e nada avisa                                        |
| --------------------------------------------------- | ------------------------------------------------------------------ |
| abrir a sessão numa subpasta                        | roda sem skill nenhuma — [regras](regras-da-camada.md)             |
| aceitar "terminei" sem ver a saída de um instrumento | você entrega o que ninguém mediu                                   |
| dar nome de página da camada a um arquivo seu       | a atualização o sobrescreve — antídoto no [mapa](mapa-do-repositorio.md) |

A atualização nunca reescreve o que é seu. A fronteira exata está no
[mapa](mapa-do-repositorio.md).
