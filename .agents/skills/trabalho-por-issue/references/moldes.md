# Moldes do trabalho por issue

Os moldes que a abertura usa. O corpo da skill diz quando abrir cada um.

## Bloco de perfil do passo zero

O bloco que se grava no perfil do repositório, em `conhecimento/projetos/`.
Os nomes são os que a casa usa, nunca os que a skill imagina:

Onde as issues moram, o padrão de nome e o fluxo do backlog **não entram
aqui**: têm casa própria, o `nucleo/configuracao.json` — um fato, uma
casa. Este bloco guarda o resto:

```markdown
## Trabalho por issue

- **Quadro de acompanhamento:** <como a casa o chama, e onde ele fica>
- **Estados do quadro, na ordem:** <os nomes de lá>
- **Rótulos que importam:** <quais, e o que cada um significa aqui>
- **Etapas de verificação:** <como a casa chama cada uma, e o que prova cada>
- **Branch onde a sessão trabalha:** <o padrão do nome, e de qual branch nasce>
- **Branch de entrega, e o que o nome dela aciona:** <esteira? implantação?
  aviso a outras pessoas?>
- **A sessão pode empurrar:** <o que sim, e o que só o dono empurra>
- **Branches protegidas** — não apagar, não renomear, não forçar, não
  reescrever: <os nomes das de longa duração. Na dúvida, é protegida.>
- **Quem encerra a issue:** <o papel, nunca o nome de uma pessoa>
- **Onde moram os procedimentos:** <a documentação de como se sobe, publica e
  libera acesso — é aqui que se procura antes de inventar passo>
```

A última linha é a que mais rende: gravada uma vez, ela faz a próxima sessão
achar a receita em vez de improvisar uma.

## Molde do corpo da issue

```markdown
## Objetivo
<uma frase: o que muda no mundo quando isto fechar>

## Escopo
Dentro: <lista curta>
Fora: <o que esta issue explicitamente não resolve>

## Critério de aceitação
- [ ] <verificável por comando ou observação — nunca por opinião>
- [ ] <...>

## Onde mexer
<caminhos e módulos. "Ainda desconhecido" é resposta válida e útil.>

## Estado
Fase: investigar | implementar | verificar
Feito: <...>
Parcial: <o que está pela metade, e onde parou>
Falta: <...>
Decisões: <uma linha cada, com link para o comentário que decidiu>

## Ponto de retomada
<o bloco da seção "Virar a sessão" da skill, reescrito a cada virada>
```

## Molde da issue para sessão sem cabeça

As cinco seções que a skill `iniciar-pedido` acrescenta **sobre** o molde de
cima, quando quem vai executar é uma sessão sem ninguém por perto. Elas
existem porque essa sessão não pode perguntar nada: o que não estiver aqui,
ela inventa ou trava.

```markdown
## O pedido, como veio
> <o texto do dono, VERBATIM — sem corrigir, resumir ou melhorar>

## O prompt para a sessão
<autossuficiente, escrito para quem não leu a conversa: o que ler antes, o
que fazer e em que ordem, o que provar, e o que não tocar. Endereço de
arquivo por NOME (função, seção); número de linha só como dica datada.>

## Onde rodar
Diretório: <o caminho do alvo, e por que é esse>
Como disparar: <painel de controle, ou o comando literal>

## Branch e trabalho em andamento
Conflita? <sim | não> — <o que a medição mostrou>
Branches recentes no mesmo assunto: <...>
Alvos paralelos: <o que `git worktree list` respondeu, e em que commit>
PRs abertos sobre a base: <número e título, ou "nenhum">

## Commit de partida
<o SHA, nunca `HEAD` nem nome de branch — os dois envelhecem entre a
declaração e a execução (regra 2)>
```

O par que faz isto valer: **pedido original e prompt refinado juntos**. O
primeiro é a âncora do que foi pedido; o segundo, o que a entrevista fechou.
Sozinho, o refinado vira a interpretação de alguém, e ninguém consegue
verificar se ela é fiel.

## Exemplos de critério de aceitação

O teste da skill: o critério começa pelo instrumento ou pelo adjetivo?

| Não serve                       | Serve                                                       |
| ------------------------------- | ------------------------------------------------------------ |
| "o login está funcionando bem"  | "`<comando de teste>` passa, incluindo o caso de senha errada" |
| "o código foi revisado"         | "a revisão apontou N achados e todos estão resolvidos ou respondidos" |
| "ficou mais rápido"             | "a mesma chamada, medida do mesmo jeito, cai de X para menos de Y" |
| "documentado"                   | "a página `<caminho>` existe e um estranho executa o passo a passo dela" |
