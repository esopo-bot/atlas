# Templates de prompt

Ache a sua situação na barra da direita, copie o bloco, preencha os
`<colchetes>`, escreva o que for seu no fim. Cola em qualquer IA.

## Como se usa

O template cru:

```
Refatore <arquivo ou módulo> para <o objetivo>.
Comportamento não muda — prove rodando <a suíte> antes e depois.
Não amplie o escopo.

--- minhas instruções ---
<escreva aqui>
```

O mesmo, preenchido:

```
Refatore o cálculo de frete para tirar a duplicação.
Comportamento não muda — prove rodando pytest tests/frete antes e depois.
Não amplie o escopo.

--- minhas instruções ---
Não mexa na tabela de preços.
Se precisar renomear alguma coisa, pergunte antes.
```

O bloco do fim é seu. Vazio, o template funciona igual. É onde entra a regra da
casa, o limite do dia, o arquivo que não se toca.

Cada situação abaixo traz, antes do prompt, uma ou duas destas linhas:

- **Aciona sozinho** — o que as palavras do prompt puxam, se você tiver a skill
  ou o plugin. O agente escolhe comparando o que você escreveu com a descrição
  de cada uma. Por isso as palavras importam.
- **Ou chame direto** — o comando, para quando você quiser pular o texto.

O padrão de qualidade de código não precisa de linha no prompt: skill de
padrão não dispara sozinha (medido: zero em 160 tentativas), então a camada a
injeta por um gancho no início de cada sessão — medido: três em três. O
contrato do gancho está em [ganchos](../conhecimento/ganchos.md). Sem o gancho
(outro agente, outra máquina), cite a skill `qualidade` pelo nome no pedido.

E uma regra que vale em todos: **diga o que é pronto.** Sem isso, "terminei" é
opinião.

## Abrir e fechar a sessão

Os dois prompts de toda sessão — a partida e o esfriamento — têm página
própria: [abrir e fechar a sessão](abrir-e-fechar-a-sessao.md). O
fechamento é a skill `esfriamento`: "O trabalho terminou. Rode o
esfriamento." resolve.

## Pedido grande, várias frentes

Quando: o trabalho tem mais de uma frente e você quer tudo entregue de uma
vez, com as decisões voltando para você no caminho.

Aciona sozinho: nada — aqui é a estrutura do pedido que organiza o trabalho.

```
Contexto: <o que já é verdade e onde estamos>.
Objetivo: <o resultado, não a lista de passos>.
Não mexa: <limites e o que fica de fora>.
Prova: <o instrumento que decide o pronto de cada frente>.
Decisões: quando a escolha for minha, pare e pergunte, com recomendação.
Entrega: trabalhe as frentes até o fim; só então me traga o resumo do que
mudou e o que ficou para eu decidir.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `pare e pergunte`. Sem ela, o agente decide por você no
meio do caminho — e pedido grande é cheio de decisões suas.

## Trabalhar no workspace, colhendo o genérico

Quando: o trabalho é no seu workspace, e a camada deve colher o que nascer
genérico nele.

Aciona sozinho: nada — a análise do fim só acontece porque o prompt a exige.

```
Trabalhe em <o workspace ou o repositório do dia>.
Contexto: <o que já é verdade>.
Objetivo: <o resultado, não a lista de passos>.
Prova: <o instrumento que decide o pronto>.

Ao terminar, antes do resumo, faça a análise de promoção:
1. Releia o que criamos e aprendemos nesta sessão.
2. Separe em três pilhas: genérico (serviria a qualquer pessoa), da casa
   (vale só para este workspace), descartável.
3. Para o genérico: diga o que promoveria para a camada, para onde (página,
   skill, gancho ou template) e o texto já abstraído — sem nome de pessoa,
   projeto, empresa ou máquina. Proponha; não aplique.
4. O que é da casa vira nota ou decisão em conhecimento/<subpasta>/.
Na dúvida se algo é genérico: é pessoal, e fica.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Proponha; não aplique`. Promoção é decisão do dono — e
camada pública não aceita resíduo pessoal.

## Entender código que não é seu

Quando: você chegou num repositório e ainda não sabe onde mexer.

Aciona sozinho: nada de fábrica — aqui o prompt faz o trabalho todo.

```
Quero entender <parte do sistema> antes de mexer.
Não altere nada.
Me diga: por onde entra, quem chama, onde o estado mora, e o que quebra se eu
mudar <a coisa>.
Aponte arquivo:linha em cada afirmação.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Aponte arquivo:linha`. Afirmação sem endereço é chute.

## Implementar algo novo

Quando: a funcionalidade não existe e o desenho ainda está aberto.

Aciona sozinho: método de levantamento de requisitos e de plano — é o próprio
texto do pedido que puxa o modo de planejamento. Para algo maior, o plugin
`feature-dev`.

```
Quero <o que a funcionalidade faz, em uma frase>.
Antes de escrever código, levante os requisitos comigo e proponha o desenho.
Com o desenho fechado, escreva o plano; só então implemente.
Pronto = <o comando ou teste que prova>.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Antes de escrever código`. É ela que puxa o levantamento.

## Corrigir um bug

Quando: o comportamento está errado e você sabe reproduzir.

Aciona sozinho: método de depuração.
Ou chame direto: `/debug`.

```
Bug: eu esperava <X> mas aconteceu <Y>.
Reproduzir: <passos ou comando>.
Ache a causa raiz antes de propor correção.
Escreva primeiro um teste que falhe por esse motivo.
Não conserte o sintoma.
Antes de concluir, rode o cético na sua conclusão.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Ache a causa raiz antes`. Sem ela, ele conserta o que está
na tela. Quando o bug está em produção e a pergunta é "o que mudou?", o
caminho inteiro está em
[investigação de incidente](investigacao-de-incidente.md).

## Escalar para outro time

Quando: a causa está fora do seu alcance e alguém precisa agir do lado de lá.

Aciona sozinho: nada — o valor aqui está no que a mensagem carrega.

```
Escreva a mensagem de escalação para <quem>, com esta espinha:
- o sintoma em uma frase, do ponto de vista de quem usa;
- o escopo MEDIDO, não amostrado: quantos afetados sobre quantos tentaram;
- o instante exato em que começou;
- os identificadores que ELES conseguem procurar no painel deles;
- o que mudou do nosso lado, com hora e autor, em tom factual;
- o pedido acionável: o que conferir, e o que fazer em cada resultado;
- como vamos validar a correção em tempo real.
Sem acusação e sem adjetivo. Se algum item não estiver medido, diga que não
está — não estime.
```

A linha que segura: `o pedido acionável`. Evidência sem pedido é escalação
pela metade: o outro time lê, concorda e não sabe o que fazer.

E a que evita despriorizar um incidente grave: **escopo medido, não
amostrado**. Três reclamações abertas podem ser 100% de quem tentou — quem
não reclama some da conta, e "três casos" vira prioridade baixa.

## Refatorar

Quando: o código funciona e está ruim de ler.

Aciona sozinho: agente simplificador.
Ou chame direto: `/simplify`. O plugin é `code-simplifier`.

```
Refatore <arquivo ou módulo> para <o objetivo>.
Comportamento não muda — prove rodando <a suíte> antes e depois.
Não amplie o escopo.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Não amplie o escopo`. Refatoração cresce sozinha.

## Revisar

Quando: a mudança está pronta e você quer um segundo par de olhos.

Aciona sozinho: revisor de mudanças.
Ou chame direto: `/code-review`. Quando o genérico não basta, o plugin
`pr-review-toolkit` traz revisores por assunto.

```
Revise o que mudou em <ramo ou diff>, procurando <bug / segurança / escopo>.
Para cada achado: arquivo:linha, por que é problema, e o caso concreto que
quebra.
Sem caso concreto, não é achado.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Sem caso concreto, não é achado`. Corta o achado plausível
que não acontece na vida real.

## Procurar falha de segurança

Quando: o que mudou toca entrada de usuário, autenticação ou dado sensível.

Ou chame direto: `/security-review`. O plugin `claude-security` aprofunda sob
demanda; o `security-guidance` avisa sozinho enquanto você edita.

```
Passe <o que mudou> atrás de vulnerabilidade.
Olhe entrada de usuário, autenticação e dado sensível.
Para cada achado: arquivo:linha e o caso concreto que explora.
Sem caso concreto, não é achado.

--- minhas instruções ---
<escreva aqui>
```

## Fechar e entregar

Quando: acabou — ou você acha que acabou.

Aciona sozinho: verificação antes de entregar.
Ou chame direto: `/verify`. O plugin `commit-commands` fecha a sequência.

```
Quero fechar <o trabalho>.
Rode <build/teste/lint> e me mostre a saída antes de dizer que passou.
Prepare o commit. O envio é meu.

--- minhas instruções ---
<escreva aqui>
```

A linha que segura: `Me mostre a saída`. É a diferença entre provar e alegar. E
o envio é seu: ação destrutiva ou de fora não é do agente.

## Atualizar as instruções do projeto

Quando: o `AGENTS.md` não descreve mais o código, e você corrige a mesma coisa
toda sessão.

Ou chame direto: `/init` escreve do zero. O plugin `claude-md-management` audita
o que já existe.

```
As instruções em <arquivo de instruções> não descrevem mais o código.
Compare as duas coisas e me diga o que está desatualizado, com arquivo:linha.
Proponha a nova redação. Não aplique sem eu aprovar.

--- minhas instruções ---
<escreva aqui>
```

## Auditar a arrumação do repositório

Quando: você desconfia que tem coisa fora do lugar — skill solta, servidor MCP
declarado em canto errado, nota na raiz, arquivo que o git não enxerga.

Aciona sozinho: nada. É o prompt que obriga a sessão a ler a regra em vez de
arrumar por gosto.

```
Auditoria da arrumação deste repositório. NÃO MOVA NADA AINDA.

1. Leia, nesta ordem, e trate como a regra que vale hoje — não use o que
   você lembra de outra sessão nem o que costuma ser padrão:
   - AGENTS.md
   - conhecimento/regras-da-camada.md (a lista numerada)
   - conhecimento/mapa-do-repositorio.md (a tabela "Onde escrever cada
     coisa" e a árvore)
   Se os três discordarem entre si, PARE e me mostre a divergência antes
   de continuar.

2. Liste o que está fora do lugar que essas páginas mandam. Procure ao
   menos: skill, servidor MCP e a declaração dele, gancho, subagente,
   comando de barra, página de conhecimento, processo, nota, rascunho e
   arquivo gerado. Para cada achado: caminho atual, caminho certo, e a
   linha da regra que decide. Sem a citação da regra, não é achado.
   Na declaração de MCP, confira também se cada caminho declarado
   (`command`, `args`, ajudantes) existe mesmo no disco — ninguém valida
   isso, e caminho morto vira servidor que não sobe sem dizer por quê.

3. Respeite a camada multi-fornecedor — ela tem uma fonte e espelhos:
   - skill nasce em .agents/skills/<nome>/SKILL.md, que é o que quase todo
     agente lê;
   - .claude/skills/ é CÓPIA GERADA: não mova nem edite nada lá. Mexeu na
     fonte, rode `python montar.py --sincronizar`;
   - .claude/ e .devin/ guardam só o que é exclusivo daquele fornecedor;
     regra que vale para todos mora no AGENTS.md.
   Mover uma skill para dentro de uma pasta de fornecedor é regressão: os
   outros agentes param de enxergá-la, e nada avisa.

4. NADA SE APAGA — nem duplicata, nem arquivo que parece morto.
   - o que está fora do lugar se MOVE com `git mv`, que preserva a história;
   - se já existe arquivo no destino, não sobrescreva: relate os dois e
     pergunte qual é a verdade;
   - o que parece sobra vira item da lista "conferir com o dono", nunca
     ação sua.

5. Rode `python montar.py` e me mostre a seção que diz se o git enxerga o
   que a camada escreveu. Arquivo criado que o .gitignore esconde não chega
   ao clone nem à sessão na nuvem.

6. Só então proponha melhorias: regra que falta, página que envelheceu,
   arquivo sem link de entrada. Proponha; não aplique.

Entregue três listas: as movimentações propostas (de → para → a regra que
manda), o que conferir comigo, e as sugestões. Espere meu OK para mover.
```

A linha que segura: `Sem a citação da regra, não é achado`. Sem ela o agente
arruma por gosto — e arrumação por gosto é a que você desfaz na semana
seguinte. A segunda é `NADA SE APAGA`: sessão que "limpa" duplicata escolhe
sozinha qual das duas versões era a verdadeira, e escolhe errado na hora que
importa.

## Conferir o trabalho de outra sessão

Quando: uma sessão trabalhou muito e você vai commitar ou publicar. A
conferência vale mais numa sessão **limpa**, que não tem apego à conclusão.

Aciona sozinho: nada. O prompt é que impede a segunda sessão de virar
torcedora da primeira.

```
Sessão de conferência. Você está auditando o trabalho NÃO PUBLICADO de outra
sessão neste repositório. Não confie nela: a saída que ela mostrou pode estar
certa e ainda assim esconder o que ela não olhou.

NÃO CONSERTE NADA. NÃO COMMITE NADA. Isto é um relatório.

Estado para você conferir, não para acreditar: <versão, número de arquivos
alterados, o que está commitado e o que não está>.

1. RODE OS INSTRUMENTOS VOCÊ MESMO — saída colada por outra sessão é
   citação, não prova. <a lista de comandos do ritual da casa>

2. ATAQUE AS AFIRMAÇÕES ABAIXO, uma a uma. Para cada: provado / provável /
   não provado, e COMO você conferiu. Se a afirmação for um número, meça de
   novo e diga o que você contou — número sem definição não se confere.
   <a lista de afirmações da sessão anterior, uma por linha>

3. PROCURE O QUE ELA NÃO OLHOU:
   - página sem link de entrada vindo de outra página;
   - afirmação nova sem instrumento por trás;
   - comando citado numa página que não roda no terminal desta máquina;
   - mesmo fato escrito em dois arquivos;
   - arquivo que o projeto cria e o git ignora;
   - o que só faz sentido numa casa específica — trocar o nome não basta, o
     desenho também entrega.

4. VEREDITO em uma linha: commita como está / commita com ressalva (qual) /
   não commita (por quê).

Entregue: a tabela das afirmações com o veredito de cada uma, a lista do que
ela não olhou, e o veredito final. Sem consertar nada.
```

A linha que segura: `RODE OS INSTRUMENTOS VOCÊ MESMO`. Saída verde colada
prova que alguém rodou algum dia, não que passa agora — e a sessão que
escreveu o texto é a menos indicada para dizer se ele está certo.

A segunda é `NÃO CONSERTE NADA`. Conferente que arruma no meio do caminho
devolve mais mudança não revisada, e você perde justamente o par de olhos
independente que foi buscar.

E `diga o que você contou` existe porque número é o achado mais fácil de
"refutar" por engano: duas medições honestas de coisas ligeiramente
diferentes discordam, e a discordância parece erro quando é definição.

## Pedir um diagnóstico a outro agente

Quando: você quer saber o que a camada **de fato** entrega a um agente — qual
deles, em qual máquina — em vez de supor. Serve para comparar ferramentas.

Aciona sozinho: nada. O valor está na ordem das partes.

```
Diagnóstico desta sessão. Responda nas partes abaixo, na ordem — a ordem
é o que faz a medição valer.

PARTE 1 — SEM ABRIR ARQUIVO NENHUM. Só do que já está carregado agora:
- Que instruções você recebeu? Cite uma frase literal de cada arquivo de
  regra que chegou até você.
- Que skills você enxerga? O nome e a descrição de cada uma.
- Que servidores MCP estão ligados, e que ferramentas cada um trouxe?
- Que subagentes e ganchos existem para você?
- Quanto de contexto tudo isso ocupou antes desta minha mensagem, na
  unidade que você consegue ver. Não consegue medir? Diga "não consigo
  medir" — não estime.
- Qual modelo está respondendo, e qual o tamanho da janela dele.

PARTE 2 — agora pode ler o disco, e compare com a Parte 1:
- O que existe em .agents/skills/, .claude/, .devin/ e nos arquivos de MCP
  que NÃO apareceu na Parte 1? Cada item é uma peça que o repositório tem e
  você não recebeu. Para cada uma, diga por que você acha que não chegou.
- O contrário também: apareceu na Parte 1 algo que não existe no disco?

PARTE 3 — o que você sabe e o que não sabe:
- Do que carregou, o que você entendeu como obrigação e o que entendeu
  como sugestão?
- O que ficou ambíguo a ponto de você ter que adivinhar?
- O que você precisaria saber e não está escrito em lugar nenhum?

PARTE 4 — sugestões para o SEU modelo, não para modelo em geral:
- Como eu deveria escrever instrução para você render mais: tamanho,
  ordem, o que pôr no começo, o que você tende a ignorar?
- O que desta camada é peso morto para você — carregado e nunca usado?
- O que você faria diferente se a janela fosse metade do que é?

Marque cada item com [GENÉRICO] (serviria a qualquer casa) ou [DA CASA] (só
vale aqui). Na dúvida: [DA CASA].
Não altere arquivo nenhum. Isto é um relatório.
```

A linha que segura: `SEM ABRIR ARQUIVO NENHUM`. Com leitura liberada o agente
abre o disco e responde certo sobre o que nunca carregou — o falso positivo
que faz a camada parecer instalada quando não está. A Parte 2 existe só para
medir a distância entre as duas respostas.

E o `[GENÉRICO]`/`[DA CASA]` no fim é o que deixa o relatório pronto para
promover: o que estiver marcado como da casa não sai do seu workspace.

## Antes de escrever skill sua

Skill que já existe é trabalho jogado fora. Corra esta peneira:

1. **Já vem de fábrica?** `/code-review`, `/security-review`, `/verify`,
   `/run`, `/simplify`, `/debug`, `/batch`, `/loop` e `/init` existem sem
   instalar nada — e a lista muda entre versões: confira com `/help`.
2. **Tem plugin oficial?** São poucos e a lista é fechada. O catálogo é
   `anthropics/claude-plugins-official`, e só é de primeira parte o que tem
   `author.name` igual a `Anthropic` no manifesto — estar no catálogo não basta.
3. **Resolve com uma frase no `AGENTS.md`?** Instrução curta vence skill nova.
4. **Sobrou o quê?** Só o que ninguém poderia ter escrito por você: a regra do
   seu negócio, o seu dado, o jeito da sua casa.
5. **Passou nos quatro?** Escreva — com o plugin `skill-creator`, que existe
   justamente para isso.

O corte do passo 4 é o que importa: **o oficial cobre técnica; você só escreve
domínio.** Uma skill chamada "corrigir bug" morre na peneira. Uma que conhece a
sua planilha, não.

## Ligar um plugin

Duas chaves no `.claude/settings.json` do projeto: de onde vem e o que está
ativo. Quem clonar o repositório recebe a sugestão junto com o código.

```json
{
  "extraKnownMarketplaces": {
    "claude-plugins-official": {
      "source": { "source": "github", "repo": "anthropics/claude-plugins-official" }
    }
  },
  "enabledPlugins": {
    "code-review@claude-plugins-official": true
  }
}
```

Ligue o que resolve um problema que você tem hoje. Cada plugin ativo ocupa
contexto, e os que dependem de programa externo falham em silêncio quando a
dependência não está instalada.
