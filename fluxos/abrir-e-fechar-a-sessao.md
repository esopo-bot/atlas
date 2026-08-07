# Abrir e fechar a sessão

Os dois momentos que se repetem em toda sessão de trabalho. O do começo é um
prompt curto; o do fim é uma linha, porque o resto virou skill.

## A partida

Cole ao abrir, com o pedido do dia no fim:

```
Siga as regras deste workspace: o AGENTS.md e a lista numerada em
conhecimento/regras-da-camada.md.
Antes de mergulhar num repositório: perfil na wiki, manifesto e pontos de
entrada primeiro — repositório grande não se varre inteiro.

Meu pedido de hoje:
```

A linha que segura: `Antes de mergulhar`. Sem ela, a sessão varre primeiro e
pergunta depois.

Num workspace com muitos repositórios, acrescente a estrutura:

```
A estrutura: os repositórios moram em projetos/ — pode haver muitos, e
grandes. Os perfis estão em conhecimento/projetos/.
Ferramentas: prefira índice e busca dirigida; rede e MCP só se a tarefa
exigir.
```

## O esfriamento

O fechamento virou a skill `esfriamento` — cético na conclusão do dia,
análise de promoção, candidato a automação, o que a próxima sessão precisa
saber, o atrito que a sessão viu e a revisão das regras. Ao terminar o dia,
uma linha basta:

```
O trabalho terminou. Rode o esfriamento.
```

Sem a skill (outro agente, outra máquina), o roteiro dela está em
`.agents/skills/esfriamento/SKILL.md` — cole os seis itens no prompt.

## O resto

Pedido grande, bug, refatoração, revisão, auditoria: cada situação tem o seu
bloco nos [templates de prompt](templates.md).
