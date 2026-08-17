# Abrir e fechar a sessão

O cartão de bolso da camada: os três blocos que se colam, na ordem em que o
dia os usa. O porquê fica no fim — leitura de uma vez.

## 1 · A partida

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

Num workspace com muitos repositórios, acrescente onde eles moram:

```
Os repositórios moram em projetos/ — pode haver muitos, e grandes. Os
perfis estão em conhecimento/projetos/. Prefira índice e busca dirigida;
rede e MCP só se a tarefa exigir.
```

## 2 · A auditoria — de tempos em tempos, antes do esfriamento

Meça a camada — não a sessão:

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

## 3 · O esfriamento — uma linha

```
O trabalho terminou. Rode o esfriamento.
```

O fechamento é a skill `esfriamento` — da análise de promoção, com o cético
na conclusão, à revisão das regras. Sem a skill (outro agente, outra
máquina), o roteiro está em `.agents/skills/esfriamento/SKILL.md` — cole os
itens no prompt.

## O porquê, para ler uma vez

Três linhas da partida fazem o trabalho pesado:

- **`em vez de descobrir`** — sem ela, a sessão varre o código para
  responder o que a wiki já responde, e chega ao seu pedido com a janela
  pela metade.
- **`não improvise a esteira`** — esteira improvisada em cima de esteira
  parece pronta e quebra longe de onde nasceu.
- **`pare e pergunte`** — sem ela, o agente decide por você no meio do
  caminho, e pedido grande é cheio de decisões suas.

**Não repita as regras no prompt.** Elas já chegam pelo `AGENTS.md` em toda
sessão; recopiá-las gasta janela duas vezes e cria uma segunda versão para
envelhecer torto. O prompt aponta e delimita — quem manda são as
[regras da camada](../conhecimento/regras-da-camada.md).

**Por que só estes três blocos:** prompt para cada situação — refatorar,
revisar, corrigir bug — a camada tinha e tirou. Eles repetiam, em texto, o
que o agente já faz por conta: `/code-review`, `/simplify` e os outros vêm
de fábrica, e a lista está no
[canivete](../conhecimento/skills-da-camada.md). O que sobrou aqui é o que
nenhuma ferramenta traz pronta: **o contorno do que a sessão pode decidir
sozinha.**
