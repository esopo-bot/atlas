# A skill que dispara

Skill que o agente não chama não existe. Esta página é a receita de escrever
uma que ele chame — e cada número aqui saiu do `.agents/gatilho/gatilho.py`,
que abre uma sessão de verdade por pedido de exemplo e registra qual skill ela
escolheu.

## A régua, antes de tudo

```bash
python3 .agents/gatilho/gatilho.py <nome-da-skill>
```

**Uma rodada não vale.** O ruído medido é de cerca de um acerto por skill: a
mesma skill, sem nenhuma mudança, oscila entre 1 e 2 de 3 em rodadas
seguidas. Compare medianas de cinco rodadas, e desconfie de qualquer
diferença menor que isso.

## O que faz uma skill disparar

**1. As palavras que a pessoa realmente digita.** É o campo que mais pesa.
As três skills que acertam 3 de 3 têm, todas, frases literais na descrição —
`"abre uma issue disso"`, `"vou encerrar por hoje"`. Descrição reescrita em
linguagem técnica, sem as frases, derrubou uma skill de 2 para 0. Escreva o
bloco:

```
Palavras que a acordam — "<o que ele digita>", "<outra>".
```

**2. Um nome curto e incomum.** Com a descrição idêntica, palavra por
palavra, um nome de uma palavra acertou 1 de 3 e um nome composto de palavras
genéricas acertou 0 de 3, em cinco rodadas. Nome longo feito de termos que
aparecem em todo lugar (`controle`, `mudanca`, `camada`) compete com o resto
do catálogo. O nome ainda tem de declarar a responsabilidade — mas entre dois
que declaram, o curto ganha.

**3. Pedido em forma de ordem, não de pergunta.** Pedido que pede parecer —
*"pode?"*, *"me diz se passa ou não"* — o modelo responde direto, sem chamar
peça nenhuma. Isso acontece mesmo com a skill sozinha no catálogo, então é
teto, não defeito: se os seus pedidos de exemplo são perguntas, 3 de 3 é
inalcançável.

## O que NÃO faz diferença

- **Gancho de abertura apontando para a skill.** Medido com os cinco ganchos
  de abertura desligados: o placar não mudou. Instrução injetada não empurra
  a escolha.
- **Descrição mais técnica.** Sozinha, não move o número. O que move é a
  frase literal.

## O preço da vizinhança

A mesma skill acerta **2 de 3 sozinha** e **1 de 3 com as outras oito no
catálogo**. Cada skill nova cobra das que já existem, além dos bytes que toda
sessão paga na largada. Antes de criar mais uma, pergunte se ela não é uma
seção de uma que já existe.

## Duas armadilhas que falham caladas

**Dois-pontos seguido de espaço na `description` quebra o YAML** do
frontmatter e invalida a skill inteira — e nada avisa na sessão, que continua
listando ela. Use travessão.

**Pasta e campo `name` divergentes** também invalidam, com o mesmo silêncio.
O gatilho recusa medir nesse caso, porque zero por skill quebrada e zero por
descrição ruim são o mesmo número — e é assim que se conclui a causa errada.

## Conteúdo duplicado por gancho não precisa de skill

Onde um gancho de abertura já injeta o texto em toda sessão, o agente não
chama a skill — e está certo em não chamar. O zero dela não é defeito: é a
medição perguntando a coisa errada. O que sobra é o custo da linha no
catálogo, paga por toda sessão para nada.

## O molde

```yaml
---
name: <curto, e diz a responsabilidade>
description: <o que faz> — <quando usar>. Escopo — <uma palavra>.
  <a vizinha que pega o resto>. Palavras que a acordam — "<frase>", "<frase>".
metadata:
  categoria: essencial | workflow | governanca | especialista
  resumo: "<uma linha, para o catálogo>"
---

...o corpo da skill...

## Pedidos de exemplo

- "<pedido em forma de ordem, do jeito que sai da boca>"
```

O `metadata` segue a especificação Agent Skills: só texto, nunca lista — agente
estrito descarta a skill calado. Por isso os pedidos de exemplo moram no
**corpo**, numa seção com esse nome exato, no fim. Eles não custam largada: o
catálogo que toda sessão paga conta apenas `name` e `description`, e o corpo só
carrega quando a skill dispara. Sem a seção, a skill sai da régua como NÃO
MEDIDA, que é honesto e inútil.
