# Roteiros que viajam com a camada

Os roteiros desta pasta são **da camada e entram no git**: o `.gitignore` ao
lado ignora tudo e libera por nome. O que a liberação não nomeia é pessoal
e fica fora — vale aqui no módulo e na `execucoes/` de quem instala.

Roteiro que mora aqui é **da camada**: não sabe nada de ninguém, tira todo
endereço da configuração, e serve a qualquer repositório que instale o
módulo. Troque a configuração e o mesmo roteiro serve outro lugar — é esse o
teste de que ele é mecanismo, e não o processo de alguém.

| Roteiro | O que faz | A seção, em "Os roteiros, um a um" |
| --- | --- | --- |
| `catalogador.json` | reorganiza a camada de conhecimento e as anotações | O catalogador |
| `entrega.json` | exemplo de trabalho que termina em pedido de revisão | O roteiro de entrega |
| `revisar-a-camada.json` | revisão periódica da camada, pela execução, e a auditoria de fora | Revisar a camada |
| `mexida-em-vizinho.json` | trabalha uma issue dentro de outro repositório do workspace | Mexida em repositório vizinho |

O `.gitignore` ao lado ignora tudo e **libera por nome**, um roteiro por
linha — nunca `!*.json`, que reabriria a pasta e deixaria roteiro local
vazar sem ninguém ver.

## A receita do disparo, em linhas copiáveis

Cada rodada nova re-pagava os mesmos pedágios por seguir prosa em vez de
linha. Aqui estão as linhas, na ordem. Troque `<n>` pelo número da issue e
`<assunto>` pelo assunto em kebab.

**1. O roteiro local.** Copie o roteiro nomeado; não edite o original.
A chave `bloco` é opcional e recorta o ESCOPO: com ela, a verificação cobra
só os `- [ ]` da seção `## Bloco N` do corpo; sem ela, cobra a issue inteira.
Bloco que o corpo não tem mata a execução com erro de uso — silêncio seria
pior.
A chave `tempo-limite-da-prova` também é opcional e vale para a rodada
inteira: é o teto, em segundos, de cada prova re-executada na verificação.
Sem ela o teto é o de sempre, 60 s. Declare-a quando a rodada tem prova
reconhecidamente demorada — suíte grande, auditor sobre uma execução
inteira. Prova avulsa que é lenta sozinha declara o teto dela no próprio
item do provado, com `"tempo-limite"`, e não precisa da chave do roteiro.

```bash
python -c "
import json
r = json.load(open('execucoes/entrega.json'))
json.dump({'auditoria': True, 'issue': <n>, **r},
          open('execucoes/roteiro-issue-<n>.json', 'w'),
          ensure_ascii=False, indent=2)"
```

**Issue que pede medição repetida declara o teto da etapa.** Etapa de sessão
morre em 3600 s, e medição que a própria issue exige — mediana de cinco
rodadas antes e cinco depois, ~550 s por conjunto — não cabe nisso: a etapa
`trabalhar` morreu com o trabalho feito e sem commit, e a retomada gastou um
ciclo refazendo o pronto. A cópia local declara `tempo-limite` na etapa que
mede, em segundos, e o ensaio mostra o teto de cada sessão antes de gastar:

```bash
python -c "
import json
r = json.load(open('execucoes/roteiro-issue-<n>.json'))
for etapa in r['etapas']:
    if etapa['nome'] == 'trabalhar':
        etapa['tempo-limite'] = <segundos>
json.dump(r, open('execucoes/roteiro-issue-<n>.json', 'w'),
          ensure_ascii=False, indent=2)"
```

**2. A árvore descartável.** Clone local, nunca worktree: o clone nasce com
`origin` apontando para o repositório daqui, e é isso que salva a entrega
quando o remoto de verdade não está disponível.

```bash
git clone --no-hardlinks . /tmp/issue-<n>
mkdir -p /tmp/issue-<n>/nucleo
cp nucleo/executor.json /tmp/issue-<n>/nucleo/
cp .mcp.json /tmp/issue-<n>/ 2>/dev/null || true
cp .git/info/exclude /tmp/issue-<n>/.git/info/exclude
```

A configuração vai para `nucleo/` DA ÁRVORE — é lá que o executor a lê.
Copiada para a raiz dela, o disparo recusa e a rodada perde o turno.

O `.git/info/exclude` **não viaja no clone** — o git o deixa para trás, e
por isso o arquivo que só ele esconde reaparece solto na árvore da
execução. Solto, ele é varrido para dentro do commit pelo `git add -A` e
conta como sujeira para a cerca da regra 16. A linha do `cp` fecha os dois
de uma vez: o que a origem escondia continua escondido na árvore
descartável.

**3. O ensaio, antes de gastar sessão.** Mesmo comando, troca a palavra.

```bash
ISSUE=<n> ASSUNTO=<assunto> \
python .agents/encadeador/encadeador.py ensaio \
  --roteiro execucoes/roteiro-issue-<n>.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias \
  --cwd /tmp/issue-<n>
```

**4. O disparo, desacoplado do terminal.**

```bash
ISSUE=<n> ASSUNTO=<assunto> \
nohup python .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/roteiro-issue-<n>.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias \
  --cwd /tmp/issue-<n> \
  > execucoes/evidencias/issue-<n>.log 2>&1 &
```

**5. A retomada, também desacoplada.** Mesma linha, com `--retomar` no fim.

**6. A auditoria à mão, antes de aprovar.** O auditor é OUTRO módulo —
instale-o com `--modulo auditor` se ainda não tiver. Sem ele, pule para o
`touch`: a aprovação é sua, com ou sem auditor.

```bash
python .agents/auditor/auditor.py execucoes/evidencias/issue-<n> \
  --cwd /tmp/issue-<n>
touch /tmp/issue-<n>/aprovacoes/entrega.ok
```

### Os quatro pedágios já pagos

- **O disparo sai da árvore intocada, e só o `--cwd` é editado.** Execução
  que mexe nos instrumentos e roda de dentro da árvore que muda derruba o
  próprio motor no meio.
- **`ISSUE` e `ASSUNTO` vão no ambiente do disparo.** Sem eles a branch de
  trabalho nasce com o nome errado, e a etapa seguinte para.
- **`--dir` resolve contra a árvore de onde o motor roda**, não contra o
  `--cwd`, e por isso vai explícito: sem ele quem for reler as evidências
  procura numa pasta vazia.
- **`aguardando-resposta` quer dizer processo MORTO.** Tocar o arquivo de
  aprovação sozinho não continua nada — quem continua é `--retomar`.

### Os pedágios que a sessão paga ao operar o motor

Medidos em rodadas anteriores; cada um custou um turno a quem não sabia.

- **Arme um vigia em segundo plano no `estado.json` do trabalho**: motor
  parado é auditoria na hora, não no fim do dia.
- **A pergunta do motor tem dois caminhos, e os dois valem.** Ele a posta na
  issue sozinho — é o registro, e é por onde o dono responde longe do
  computador. Com o dono na conversa, encurte: leia a pergunta na evidência
  da etapa, faça-a como pergunta de uma escolha com recomendação, e devolva
  a resposta com `--retomar --resposta "..."`. O que é mecânica, e não
  decisão — aplicar um patch que a cerca impediu, por exemplo —, resolva você
  e só relate.
- **O auditor à mão roda SEM `PROJETO` na frente**: a execução gravou o
  ambiente em `ambiente.json`, ao lado do `estado.json`, e o auditor o repõe;
  a variável no shell é ignorada onde esse arquivo existe. Para apontar as
  provas a outro alvo, edite o `ambiente.json` da pasta.
- **A branch de trabalho JÁ ESTÁ no remoto quando você vai integrar**: a
  etapa `trabalho-empurrado` a empurrou da árvore descartável assim que o
  commit existiu. Não busque à mão — confira com `git rev-parse <branch>` e
  mescle `--no-ff` na integração, depois o push. Rode o ritual DEPOIS da
  mescla, porque o que veio da integração entra na conta. Depois: critérios
  com saída colada na issue, feche-a, pode a linha da caixa com o commit,
  apague a branch entregue.
- **A sessão do motor que gasta o teto sem commitar declara `segue` vazio**,
  e a retomada a pula: preserve a trilha, deixe o mapa no ponto de retomada
  da issue (arquivos, ordem, "commite cedo") e recomece a execução.

## Os roteiros, um a um

### O catalogador

O roteiro `catalogador.json`, ao lado, é a rotina fixa que reorganiza a
camada de conhecimento e as anotações do workspace.

O CATALOGADOR — a rotina fixa que reorganiza a camada de conhecimento e as anotações do workspace.

Roteiro da CAMADA: viaja com o módulo, não sabe nada de ninguém, e por isso todo endereço sai da configuração.

O dono a invoca quando quiser; ela NUNCA roda sozinha.

Ela não commita: deixa o diff para revisão.

O alcance é limitado por CÓDIGO — o gancho vetar-conhecimento-em-codigo.py barra escrita em diretório só de código, e a etapa de verificação acusa qualquer toque fora do permitido, inclusive em nucleo/.

#### Como rodar o catalogador

```bash
python .agents/encadeador/encadeador.py ensaio \
  --roteiro execucoes/catalogador.json \
  --trabalho catalogador --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/catalogador.json \
  --trabalho catalogador --dir tmp/evidencias --cwd .
```

O ensaio primeiro, sempre. E **o dono invoca**: esta rotina não tem
agendamento e não roda sozinha.

### O roteiro de entrega — um EXEMPLO, não o processo do seu repositório

`entrega.json`, ao lado, mostra a forma de um trabalho que termina em pedido
de revisão. **Ele é exemplo, e cada nome dentro dele sai da configuração** —
a camada não tem opinião sobre a topologia do seu repositório.

#### O que ele demonstra

Os estágios, na ordem do `entrega.json`: abrir a branch de trabalho a partir
da base declarada → trabalhar → medir se o trabalho foi commitado →
**empurrar a branch para o repositório durável** → **revisar o diff pela
régua da stack** → **revisão geral do diff, por sessão independente** → medir se o
resultado entra na branch de integração declarada → verificação → escrever o
corpo do pedido de revisão → aprovação manual.

O estágio que revisa pela régua da stack lê a stack de CONFIGURAÇÃO —
`projetos.<projeto>.stack`, em `nucleo/executor.json` —, nunca da extensão dos
arquivos. Sem stack declarada ele passa com recado, em vez de quebrar a rodada
ou inventar uma régua que ninguém pediu: a camada não tem opinião sobre a
stack de quem instala. Ele lê e opina; consertar é de quem trabalha.

O estágio que empurra existe por uma medição: a árvore de trabalho costuma
ser descartável — em muitas máquinas `/tmp` é memória, não disco — e trabalho
commitado que nunca saiu dela some com ela, sem log e sem aviso. O estágio
empurra assim que o commit existe e prova o destino com
`git ls-remote --heads origin <branch>`; se a branch não chegou, ele reprova
e a execução para ali, antes de qualquer espera.

**Nada disso é obrigatório.** Se o seu repositório entrega direto na base,
apague os estágios do meio; se não usa branch de integração, tire o estágio
que mede o merge. O que o exemplo ensina não é a topologia — é que **a
fronteira é de etapa, não de sempre**: a etapa de trabalho só commita na
branch de trabalho, e quem leva o resultado para a branch de integração
declarada é a ENTREGA, depois da aprovação manual. Mesclar a branch de
publicação e publicar seguem do dono, sempre. E o corpo do pedido cobre
o que o diff entrega.

#### O que sai da configuração no roteiro de entrega

| No roteiro | De onde vem |
| --- | --- |
| a base da branch de trabalho | `branches.base` |
| o nome da branch | `branches.padrao_de_trabalho` |
| onde o trabalho é medido | `branches.integracao` |
| o que a automação pode fazer | `autorizacoes`, em `nucleo/configuracao.json` |
| a régua do revisor de diff | `projetos.<projeto>.stack` |

Troque a configuração e o mesmo roteiro serve outro repositório. É esse o
teste de que ele é mecanismo, e não o processo de alguém.

#### As quatro seções do pedido de revisão

O estágio que escreve o corpo exige, com estes títulos: **o que foi
testado** (comando e saída), **risco de quebrar em produção**, **mitigação**
e **plano de reversão** — incluindo o que a reversão *não* desfaz. Quem abre
o pedido é o dono, com o texto na mão.

### Mexida em repositório vizinho

Este roteiro faz o trabalho de uma issue **dentro de outro repositório do
seu workspace**, sem instalar a camada nele. O alvo é um repositório de
código, e continua sendo depois que a execução sai.

A configuração continua sendo lida da **raiz do workspace**; o que muda é
onde o `git` roda. O alvo chega por variável de ambiente:

```sh
PROJETO=<caminho-do-repositorio-alvo> ISSUE=<n> ASSUNTO=<assunto-em-kebab> \
  python .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/mexida-em-vizinho.json \
  --trabalho issue-<n> \
  --dir execucoes/evidencias
```

#### As três recusas, e o porquê de cada uma

O primeiro estágio é a barreira. Ele recusa antes de tocar em qualquer
coisa, e a mensagem diz o motivo — recusa muda que não se explica vira
tentativa de adivinhar de novo.

| Quando | Por que recusa |
| --- | --- |
| `PROJETO` não veio | adivinhar alvo é escrever no lugar errado |
| o alvo não tem `.git` | só sabe trabalhar dentro de um repositório |
| o alvo é somente leitura | dele se lê, nele não se escreve |

**A lista de somente leitura não mora no roteiro.** Ela sai de
`nucleo/executor.json`: cada projeto se declara em `projetos.<etiqueta>`, e o
que tem `somente_leitura: true` entra na lista pelo nome do `repositorio`. O
gancho `.claude/hooks/vetar-escrita-em-somente-leitura.py` deriva a lista da
MESMA chave — por isso a recusa vale por qualquer caminho, não só por este
roteiro. Fato repetido em dois lugares envelhece torto e passa a mentir de um
dos lados, e é por isso que os dois leem o mesmo campo.

O molde está em `nucleo/executor.exemplo.json`, que viaja com a camada.

#### Os cinco estágios

| Estágio | O que prova |
| --- | --- |
| `abrir-branch-no-vizinho` | a branch nasceu no alvo, no commit da base |
| `trabalhar` | a sessão faz o pedido da issue, dentro do alvo |
| `trabalho-commitado` | alvo limpo, commit novo, nada mexido fora |
| `trabalho-empurrado` | a branch chegou ao repositório durável do alvo |
| `verificacao` | as provas dos estágios re-executam e batem |

Toda prova roda a partir da raiz do workspace e chega ao alvo por
`git -C "$PROJETO" ...`. É isso que deixa a verificação re-executar:
caminho de máquina escrito à mão morre na primeira máquina diferente.

A prova de commit novo ancora no **SHA** da base, não em `origin/<base>`.
Ref que anda envelhece a prova antes de a verificação chegar nela.

#### Empurrar no alvo, sem empurrar cego

Commit que fica só na árvore do alvo não existe para o resto do mundo, e
some no dia em que aquela pasta sumir — é a regra 16. Por isso o estágio
`trabalho-empurrado` leva a branch de trabalho ao repositório durável do
alvo e prova o destino comparando o `rev-parse HEAD` do alvo com o
`ls-remote --heads origin` dele. Sha diferente é trabalho que não chegou;
remoto que não respondeu é **não medido**, nunca "chegou".

Cego ele não empurra. Antes, procura a etiqueta do alvo — o nome da
pasta de `PROJETO` em `projetos.<etiqueta>.repositorio` — e para
quando a resposta do cadastro é não:

| Quando | O que ele diz |
| --- | --- |
| o alvo não tem etiqueta declarada | falta `projetos.<etiqueta>.repositorio` com o nome da pasta |
| o cadastro diz `somente_leitura` | o caminho é pedido de incorporação como sugestão, com o `revisor` declarado |
| `autorizacoes.push` não está ligado | omissão não é permissão: ligue a chave, ou peça ao dono |

As três leem a MESMA chave que os ganchos leem — o de somente leitura e o
de branch protegida. Empurrar cego bateria na cerca e pararia a execução
com um erro que não ensina nada.

#### O que a mexida NÃO faz

- Não abre pedido de incorporação, e não mescla. Publicar é do dono.
- Não empurra onde o cadastro do alvo não autoriza.
- Não escreve fora do alvo — e isso é medido, não pedido: se a árvore do
  workspace ficar suja, `trabalho-commitado` reprova.
- Não instala a camada no alvo. Nada de `.agents/`, `conhecimento/` ou
  `nucleo/` copiados para lá.

#### O que sai da configuração na mexida em vizinho

| No roteiro | De onde vem |
| --- | --- |
| a base da branch de trabalho | `projetos.<etiqueta>.branches.base`; sem ela, `branches.base` da raiz |
| o nome da branch | `projetos.<etiqueta>.branches.padrao_de_trabalho`; sem ela, `branches.padrao_de_trabalho` da raiz |
| quais repositórios são somente leitura | `projetos.<etiqueta>.somente_leitura` |
| se a automação pode empurrar no alvo | `projetos.<etiqueta>.autorizacoes.push` |
| a quem sugerir o pedido de incorporação | `projetos.<etiqueta>.revisor` |
| o repositório alvo | a variável `PROJETO` |
| o número da issue e o assunto | as variáveis `ISSUE` e `ASSUNTO` |

Cada projeto pode declarar o seu bloco `branches` dentro do cadastro, e só
o que ele declarar vale para ele: o bloco da raiz é o padrão de quem não
declara. Assim um vizinho cuja integração é `develop` convive com uma raiz
cuja integração é `homolog`, sem mudar nada no repositório do vizinho.

Troque a configuração e o mesmo roteiro serve outro workspace — é esse o
teste de que ele é mecanismo, e não o processo de alguém.

### Revisar a camada

O roteiro `revisar-a-camada.json`, ao lado, mede a camada de IA **deste**
repositório e diz se ela ainda paga o que cobra.

Ela responde três perguntas, nesta ordem, e nenhuma delas por opinião:

1. **Quanto a camada cobra?** Quantos bytes toda sessão paga antes de fazer
   qualquer coisa — as instruções mais o catálogo de skills. O corpo de cada
   skill não entra nessa conta: ele só é cobrado quando a skill dispara.
2. **A camada se prova?** Todo gancho e todo instrumento roda o próprio
   `--testar`, e o instalador verifica se o que ele carrega embutido bate com
   o disco. Gancho sem teste é acusado pelo nome.
3. **Uma sessão de verdade lê e aplica as regras?** Uma sessão sem dono por
   perto abre neste repositório, lê a camada e responde seis perguntas sobre
   as regras dela — onde abrir a sessão, quantas regras existem, se pode
   commitar, o que fazer com segredo, o que fazer com branch de longa
   duração, o que é pronto. Depois escreve um script pequeno, e duas
   checagens medem se o teste que ela escreveu passa e se ele exercita o
   próprio código. A correção é programática: comparação com
   `nucleo/regras.json` e leitura de AST. Não há juiz de IA.

#### O que a revisão NÃO faz

Não commita, não empurra, não publica e não conserta nada. Ela mede e
relata; o que fazer com o número é de quem lê.

#### Como rodar a revisão

```bash
python .agents/encadeador/encadeador.py ensaio \
  --roteiro execucoes/revisar-a-camada.json \
  --trabalho revisar-a-camada --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/revisar-a-camada.json \
  --trabalho revisar-a-camada --dir tmp/evidencias --cwd .
```

O ensaio lista os estágios sem executar nada. A etapa `sessao-simulada` gasta
uma sessão de verdade: é a única que custa dinheiro, e a única cujo número
varia sozinho. Acurácia que cai pede uma segunda rodada antes de virar
achado.

#### Onde os números moram

Cada etapa grava uma evidência em `<dir>/<trabalho>/`. As provas são
comandos re-executáveis que imprimem um número só — o `--numero` do
`camada.py` existe para isso, e é o que a etapa de verificação re-roda.

#### O método, quando a revisão é sua e não do roteiro

O roteiro acima mede. Quando a revisão é conduzida por alguém — lendo,
perguntando, propondo —, o que separa revisão de opinião é a régua abaixo.

##### A régua de uma proposta

Proposta só existe com três partes. Sem as três, não é proposta:

1. **O problema, medido** — comando rodado e saída colada. Para achado vindo
   de fora, o endereço da fonte no lugar do comando.
2. **O custo de deixar como está** — em quê isso morde: estabilidade, tempo,
   contexto, dinheiro da sessão, ou risco de quem instalar a camada.
3. **O instrumento que provaria o conserto** — o que vai ficar verde depois.

Está proibido: *poderia ficar mais limpo*, *boa prática recomenda*, *seria bom
padronizar*, *a versão nova tem isso*. Quem não consegue medir tem uma
**pergunta aberta**, e pergunta aberta se registra como pergunta — nunca como
tarefa.

##### A ordem de executar o que passou na régua

- Estabilidade antes de economia, economia antes de performance, performance
  antes de estética.
- **Menor diff coerente**: uma entrega que passa sozinha por vez.
- Arrumação e mudança de comportamento não andam no mesmo passo — diff
  misturado ninguém revisa.
- Antes de começar e antes de terminar: `git status --short`. Arquivo que
  mudou e não é seu é outra sessão — pare e avise.

##### A definição de pronto

Tudo medido, sem exceção: o ritual verde, todo `--testar` em OK e **nenhum
piso abaixo** da última medição registrada, o instalador dizendo que está tudo
em dia, e `git status --short` mostrando só o que se quis mudar. Onde o
repositório publicar para fora, o ensaio da publicação entra na conta — e
quem não publica não tem esse passo.

A medida que **varia sozinha** é a sessão simulada, porque é uma sessão de
verdade. A regra dela: caiu, rode de novo antes de chamar de achado; caiu duas
vezes seguidas, é achado — e olhe **qual** checagem caiu, não só o placar.

##### Quando não há nada a fazer, e quando as barreiras barram

Diga isso, com a medição junto, e pare. **Não invente trabalho.** Um "nada a
fazer" provado vale mais que uma refatoração inventada, e a revisão seguinte
começa sabendo onde já se olhou. Vale por pergunta: dez perguntas com achado e
uma sem é revisão normal; dez perguntas com achado forçado é revisão perdida.

Há o outro fim, que também não é fracasso: **uma barreira barrou.** Gancho, veto e
doutrina são calibrados por quem não vai executá-los, então param a sessão por
tolerância que ninguém previu — não por erro dela.

Quando acontecer: **não contorne, não peça exceção, e não trate como falha
sua.** Registre a parada com o comando que a disparou e a tolerância que
faltava, e siga o que der para seguir. A lista dessas paradas é a matéria-prima
para recalibrar as barreiras, e é a única forma de a régua melhorar sem
alguém afrouxá-las no susto.

#### A auditoria externa: prove que a camada merece existir

Receita para uma sessão **de fora**: outro modelo, outra conta, contexto
limpo. Peça que ela a siga inteira, aberta na raiz do repositório da camada.

Seu papel não é ajudar. É **derrubar**. A camada tem de se provar diante de
você, não o contrário.

##### Por que uma sessão de fora

O ritual do repositório tem as suas rotinas e elas passam verdes com defeito
grave dentro. Já aconteceu: um instrumento nunca conseguiu mover o cartão do
quadro por falta de permissão e a recusa aparecia como "não achei" — semanas
assim, ritual verde o tempo todo. Ritual verifica o que alguém pensou em
verificar. **Você existe para olhar o que ninguém pensou.**

##### A regra que vale acima de todas

**Meça antes de afirmar.** Este repositório recusa opinião: cada afirmação
sua precisa vir com o comando que a produziu e a saída colada. Achado sem
medição é palpite, e palpite aqui custa mais caro que silêncio.

E **uma medição não é medição**. Onde houver variação — escolha de modelo,
tempo, custo —, o ruído engole diferenças pequenas. Compare medianas de cinco
execuções, e desconfie de qualquer diferença menor que o ruído que você
mediu.

##### O que a sessão de fora faz, nesta ordem

###### 1. Entenda antes de julgar

- [ ] `cat AGENTS.md` e `cat CLAUDE.md` — as instruções que toda sessão paga.
- [ ] `python verificacoes.py` — a lista das rotinas e o que cada uma prova.
- [ ] `python verificacoes.py ritual` — rode e leia a saída inteira. Ela passa
      de 100 KB: leia por seção, com `grep` ou `awk`, em vez de abrir tudo de
      uma vez — leitor que estoura o teto de saída perde o fim, que é onde
      mora o veredito.
- [ ] `python verificacoes.py instalada` — **esta não está no ritual** e é a
      que roda o `--testar` de cada gancho e instrumento. Rode sempre.
- [ ] `python .agents/camada/camada.py --largada` — o que toda sessão paga
      antes de trabalhar, e o teto declarado.

###### 2. Ataque a premissa, não a implementação

Para cada peça que você encontrar, pergunte nesta ordem:

1. **Isto resolve um problema real, ou um problema imaginado?** Peça sem
   caso de uso medido é peso. Procure quem a chama: se ninguém chama, diga.
2. **Isto já existe pronto?** Compare com o que a ferramenta oficial já
   traz, com o que o ecossistema tem, e com o que outra peça daqui já faz.
   Cite a fonte oficial — versão e data — quando disser que existe.
3. **A prova dela prova mesmo?** Teste que não falha quando o código quebra
   não é teste. Quebre de propósito e veja se alguém acusa.
4. **O que ela custa a toda sessão?** Bytes de largada, tempo, tokens.
   Compare o custo com o problema que ela resolve.

###### 3. Procure o caminho de erro que ninguém escolheu testar

É onde os defeitos moram. Especificamente:

- [ ] Função que **engole exceção em volta de uma conta**: falha vira zero, e
      zero parece fato.
- [ ] Verificação que enumera **o que ignora** em vez de declarar **o que
      prova**: cada peça nova do repositório vira falso positivo.
- [ ] Cópia gerada que diverge da fonte sem ninguém acusar.
- [ ] Cerca que barra por uma via e cala por outra — o mesmo efeito por
      `Edit` e por `Bash`, por exemplo.
- [ ] Cerca que reconhece uma **lista fechada de programas**: liste todo
      programa que o parser de comando conhece e pergunte o que produz o
      mesmo efeito e NÃO está na lista. A falha mora dentro do mesmo canal,
      não entre canais — `curl -o`, `wget -O`, `rsync`, `perl -i` e
      `dd of=` escrevem tanto quanto `rm`, `mv`, `cp`, `tee` e `sed -i`, e
      atravessam a cerca de escrita que só conhece estes.
- [ ] **Antes de atacar um gancho, leia a issue mais recente que o tocou**
      (`gh issue list --search "<nome do gancho>"`). Achado que a issue já
      discutiu e deixou fora de propósito não é achado — é comentário nela.
- [ ] Recusa de permissão que aparece como "não encontrei".

###### 4. Consulte a documentação oficial, e cite

Onde a camada usa ferramenta de terceiro, confira contra a documentação
oficial **de hoje**, não contra a sua memória. Diga a versão que consultou.
Se a camada usa um recurso descontinuado, ou deixa de usar um que resolveria
melhor, isso é achado de primeira ordem.

##### O que fazer com o que você achar

**Achado vira linha no quadro, não arquivo:**

```bash
python .agents/caixa/caixa.py defeito --id <kebab-minusculo> --assunto "<o achado inteiro, com a medição e o comando que a replica>"
python .agents/caixa/caixa.py melhoria --id <kebab-minusculo> --assunto "<idem>"
```

Uma linha por achado, com o comando que o reproduz. Sem isso, quem ler não
consegue reproduzir e o achado morre.

**Mudança de regra se PROPÕE, não se aplica.** Regra, gancho e política são
do dono. Escreva a proposta com a medição que a sustenta e pare.

**Feche mais do que abre.** Antes de abrir issue nova, procure a existente:
`gh issue list --repo <declarado em nucleo/executor.json>`. Achado que já tem
linha no quadro vira comentário nela, não linha nova.

##### Onde a sessão de fora NÃO manda

- **Publicar é do dono.** Seu teto é `python publicar.py --ensaio` — e ele
  clona o espelho e exige conta ativa no `gh`. Para varrer só o conteúdo do
  que o git rastreia, sem rede, sem clone e sem conta:
  `python publicar.py --varredura`, que sai 1 nomeando o arquivo quando acha
  nome próprio, credencial ou caminho de máquina.
- **Destrutivo é do dono.** Não apague nada; proponha, com a razão.
- **Não edite cópia gerada.** A fonte é a que viaja; a cópia se regenera.
- **Nada de segredo, nome de pessoa, de empresa ou caminho de máquina** em
  arquivo, commit ou issue. Este repositório é público.

##### Como a sessão de fora encerra

- [ ] O que você **mediu**, com comando e saída colados.
- [ ] O que você **derrubou** — afirmação da camada que não se sustentou.
- [ ] O que você **não conseguiu derrubar**, que é o valor de verdade: peça
      que resistiu a um ataque honesto está mais provada que antes.
- [ ] As linhas que você pôs no quadro, por identidade.
- [ ] **Uma crítica a este prompt**: o que ele te fez perder tempo olhando, e
      o que ele deixou de mandar você olhar. A régua sobe a cada rodada, e
      quem a levanta é você.

## Onde mora o SEU roteiro

Na `execucoes/` da raiz do seu repositório. Lá o conteúdo não entra no git,
de propósito: roteiro de trabalho cita o caminho da sua máquina, o nome dos
seus outros repositórios, o seu caso. Nada disso viaja.

Quando um roteiro seu deixar de citar o seu caso e passar a servir qualquer
repositório, ele é candidato a mudar para cá — e aí precisa da linha no
`.gitignore` e da seção dele em "Os roteiros, um a um", acima.
