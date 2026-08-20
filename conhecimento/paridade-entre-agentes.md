# Paridade entre agentes: o que porta e o que não porta

A camada nasceu no Claude Code e roda em mais de um agente. O que decide se
ela funciona no outro **não é o fabricante ter o mecanismo** — é como o gancho
foi escrito.

## Conclusão primeiro

Medido em 18/08/2026, com o Devin como segundo agente: ele **tem** o mecanismo
completo de ganchos, com mais eventos que o Claude, e lê o
`.claude/settings.json` sem tradução nenhuma. Quando os ganchos não disparam,
a causa está em **três parafusos frouxos na camada**, não no agente. Os três
se apertam por configuração, sem escrever motor novo.

## Os três parafusos

| # | Parafuso | O que quebra |
| --- | --- | --- |
| 1 | a ponte para a `.claude` desligada | o agente **nem lê** o `settings.json`: nenhum gancho é carregado |
| 2 | `${CLAUDE_PROJECT_DIR}` no comando | o outro agente não define essa variável; o caminho vira `/.claude/hooks/x.py` e **todo gancho morre** com arquivo inexistente |
| 3 | `matcher` com o nome de ferramenta de um fabricante só | os nomes mudam entre agentes, inclusive a caixa; `matcher` é regex sensível a maiúscula, não casa, e o gancho não dispara |

O segundo é o mais traiçoeiro: o gancho existe, está ligado, e falha em
silêncio — o agente não acha o arquivo e segue como se nada tivesse sido
declarado.

## O que porta, e o que não

**Porta:** a decisão de recusa. O contrato
`hookSpecificOutput.permissionDecision: "deny"` é honrado, e o comando é
bloqueado de verdade. **O muro atravessa.**

**Não porta:** o `additionalContext` em `PreToolUse` — ele é descartado em
silêncio. **A lição não atravessa.**

Essa é a assimetria que importa, e ela tem consequência de desenho: um gancho
que só ensina vira inerte no segundo agente, enquanto um gancho que barra
continua barrando. Onde a regra precisar valer nos dois, **ela tem de barrar,
não só avisar** — e a explicação vai junto do `permissionDecisionReason`, que
viaja com a recusa.

## Como se mede isto num agente novo

Não confie na documentação: rode.

1. Ligue um gancho que recusa e um que só injeta contexto.
2. Dispare os dois com a ferramenta que o `matcher` declara.
3. Veja qual dos dois chegou. Falha em silêncio é o resultado esperado quando
   um dos três parafusos está frouxo — então teste o caminho do arquivo
   **imprimindo-o**, antes de concluir que o mecanismo não existe.

A armadilha de medição: gancho que não dispara e gancho que dispara e é
ignorado parecem iguais de fora. Só se separam por dentro — ver
[falso negativo](falso-negativo.md).

## Onde a paridade não fecha

Nomes de ferramenta e eventos não são padronizados entre fabricantes, e não
existe contrato comum publicado. Cada agente novo pede a medição acima. O que
a camada pode fazer — e faz — é escrever o gancho de modo que ele **não
dependa** de variável de ambiente de um fabricante só, e declarar o `matcher`
com os nomes de todos os agentes que o repositório usa.

Ver também [ganchos](ganchos.md), que é onde o mecanismo está explicado.
