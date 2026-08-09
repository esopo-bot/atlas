# Abrir e fechar a sessão

Os dois momentos que se repetem em toda sessão. O do começo é um prompt que
você cola; o do fim é uma linha, porque o resto virou skill.

## A partida

Cole isto, com o seu pedido no fim:

```
Siga o AGENTS.md desta raiz e a lista numerada em
conhecimento/regras-da-camada.md. Se eu disser algo que divirja delas,
pare e me mostre a divergência.

O que já está escrito, você lê em vez de descobrir: as subpastas de
conhecimento/ são a memória desta casa. Consulte antes de varrer código
ou de decidir de novo.

Procedimento que esta casa já tem se procura na documentação dela. Não
achou? Peça o endereço; não improvise a esteira.

O que é pronto e o que não é seu estão na lista. Quando a decisão for
minha, pare e pergunte — uma por vez, com a sua recomendação primeiro.

Anote, enquanto trabalha, cada vez que tiver de adivinhar algo que esta
camada deveria ter dito. A lista sai no fechamento, com o endereço da
página que deveria ter avisado.

Meu pedido de hoje:
```

Três linhas fazem o trabalho pesado:

- **`em vez de descobrir`** — sem ela, a sessão varre o código para
  responder o que a wiki já responde, e chega ao seu pedido com a janela
  pela metade.
- **`não improvise a esteira`** — esteira improvisada em cima de esteira
  parece pronta e quebra longe de onde nasceu.
- **`pare e pergunte`** — sem ela, o agente decide por você no meio do
  caminho, e pedido grande é cheio de decisões suas.

Num workspace com muitos repositórios, acrescente onde eles moram:

```
Os repositórios moram em projetos/ — pode haver muitos, e grandes. Os
perfis estão em conhecimento/projetos/. Prefira índice e busca dirigida;
rede e MCP só se a tarefa exigir.
```

**Não repita as regras aqui.** Elas já chegam pelo `AGENTS.md` em toda
sessão; recopiá-las no prompt gasta janela duas vezes e cria uma segunda
versão para envelhecer torto. Este prompt aponta e delimita — quem manda são
as [regras da camada](../conhecimento/regras-da-camada.md).

## A auditoria da sessão

De tempos em tempos, antes do esfriamento, meça a camada — não a sessão:

```
A sessão vai fechar. Antes do esfriamento: o que a CAMADA falhou em
dizer — não o que você aprendeu. Quatro perguntas; resposta sem o
endereço da página que deveria ter avisado não entra:

1. O que você teve de descobrir que a camada já sabia? Onde estava?
2. O que você errou que uma linha teria evitado? Qual linha, em qual página?
3. O que você carregou e não usou?
4. O que você procurou e não achou — e onde procurou primeiro?

Junte as anotações de adivinhação feitas durante o trabalho.
"Poderia ser mais clara" é ruído; achado é linha faltante, com endereço.
```

## O esfriamento

O fechamento é a skill `esfriamento` — da análise de promoção, com o cético
na conclusão, à revisão das regras. Uma linha basta:

```
O trabalho terminou. Rode o esfriamento.
```

Sem a skill (outro agente, outra máquina), o roteiro está em
`.agents/skills/esfriamento/SKILL.md` — cole os itens no prompt.

## Por que só estes dois

Prompt para cada situação — refatorar, revisar, corrigir bug — a camada
tinha e tirou. Eles repetiam, em texto, o que o agente já faz por conta:
`/code-review`, `/simplify`, `/debug` e os outros vêm de fábrica e a lista
está no [canivete](../conhecimento/skills-da-camada.md). Modelo de prompt para
o que já tem comando é uma casa a mais para envelhecer.

O que sobrou aqui é o que nenhuma ferramenta traz pronta: **o contorno do que
a sessão pode decidir sozinha.**
