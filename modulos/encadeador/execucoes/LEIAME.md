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
- **O passo e o desfecho moram no corpo.** A cada etapa o motor reescreve o
  bloco da execução no corpo da issue, entre as marcas dele: a lista das
  etapas, o detalhe da última e o desfecho. Comentário, com a marca de
  `issues.quem_se_marca`, só a pergunta ao dono — e a resposta vale para a
  etapa que perguntou, nunca para a aprovação seguinte.
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

Na raiz que se declarou espelho da integração
(`git config camada.raizSoEspelhaAIntegracao true`), a etapa que reescreve
página rastreada é recusada ali: rode com `--cwd` numa worktree da
integração (`git worktree add .claude/worktrees/catalogador
origin/<integração>`), e o diff fica nela para a revisão.

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
declarada é a ENTREGA, depois da aprovação manual. Mesclar o pedido
aprovado segue `autorizacoes.mesclar` da raiz (regra 9); publicar segue do
dono, sempre. E o corpo do pedido cobre o que o diff entrega.

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
e **plano de reversão** — incluindo o que a reversão *não* desfaz. Abrir o
pedido com esse texto é da sessão; aprová-lo é do dono, e a mescla segue
`autorizacoes.mesclar` (regra 9).

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

O roteiro `revisar-a-camada.json` mede a camada deste repositório e diz se
ela ainda paga o que cobra, sem opinião: quanto ela cobra de largada, se
todo gancho e instrumento roda o próprio `--testar`, e se uma sessão de
verdade lê e aplica as regras (seis perguntas corrigidas contra
`nucleo/regras.json`, mais um script pequeno lido por AST; sem juiz de IA).
Ela não commita, não empurra, não publica e não conserta.

```bash
python .agents/encadeador/encadeador.py ensaio   --roteiro execucoes/revisar-a-camada.json   --trabalho revisar-a-camada --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar   --roteiro execucoes/revisar-a-camada.json   --trabalho revisar-a-camada --dir tmp/evidencias --cwd .
```

A etapa `sessao-simulada` gasta uma sessão de verdade e é a única cujo
número varia sozinho: caiu, rode de novo antes de chamar de achado; caiu
duas vezes, é achado, e olhe qual checagem caiu. Cada etapa grava a
evidência em `<dir>/<trabalho>/`, com provas que são comandos
re-executáveis que imprimem um número só (o `--numero` do `camada.py`).

#### A régua de uma proposta

Proposta tem três partes, senão não é proposta: o problema medido (comando e
saída colada, ou o endereço da fonte), o custo de deixar como está, e o
instrumento que provaria o conserto. "Poderia ficar mais limpo" e "boa
prática recomenda" não entram; quem não consegue medir tem pergunta aberta,
e pergunta aberta se registra como pergunta. Ordem de execução:
estabilidade, economia, performance, estética; menor diff coerente;
arrumação e comportamento em passos separados. Pronto é tudo medido: ritual
verde, todo `--testar` em OK, nenhum piso abaixo da última medição, o
instalador em dia e `git status --short` só com o que se quis mudar.
"Nada a fazer" provado vale mais que trabalho inventado; barreira que
barrou não é falha sua: registre o comando e a tolerância que faltou.

#### A auditoria externa: prove que a camada merece existir

Receita para uma sessão de fora (outro modelo, outra conta, contexto
limpo), aberta na raiz. O papel dela é derrubar: o ritual verifica o que
alguém pensou em verificar, e já passou verde com defeito grave dentro.

1. **Meça antes de afirmar.** Cada afirmação vem com o comando e a saída
   colada; onde houver variação, mediana de cinco execuções.
2. **Entenda antes de julgar:** `AGENTS.md`, `CLAUDE.md`,
   `python verificacoes.py` (a lista), `python verificacoes.py ritual` (leia
   por seção), `python verificacoes.py instalada` (a bancada de tudo, fora
   do ritual) e `python .agents/camada/camada.py --largada`.
3. **Ataque a premissa:** isto resolve problema real ou imaginado (quem
   chama?); já existe pronto na ferramenta oficial ou noutra peça daqui
   (cite versão e data); a prova prova mesmo (quebre e veja quem acusa); o
   que custa a toda sessão.
4. **Procure o caminho de erro que ninguém testou:** exceção engolida em
   volta de conta (falha vira zero); verificação que enumera o que ignora;
   cópia gerada que diverge calada; cerca que barra por `Edit` e cala por
   `Bash`; cerca com lista fechada de programas (`curl -o`, `wget -O`,
   `rsync`, `perl -i`, `dd of=` escrevem tanto quanto `rm` e `sed -i`);
   recusa de permissão que aparece como "não encontrei"; conserto de
   conserto comparado só com a base. Antes de atacar um gancho, leia a
   issue mais recente que o tocou.
5. **Confira contra a documentação oficial de hoje**, com a versão.

Antes de virar linha, o achado passa pelos céticos. No Claude Code, a rodada
é o workflow salvo `/ceticos` (`.claude/workflows/ceticos.js`); a skill
`verificacao-adversarial` diz quando e com que `args` chamá-lo.

Achado vira linha no quadro, com o comando que o reproduz:
`python .agents/caixa/caixa.py defeito|melhoria --id <kebab> --assunto "..."`.
Regra, gancho e política se propõem, não se aplicam. Feche mais do que
abre: achado com linha no quadro atualiza a linha. Publicar é do dono (o
teto é `python publicar.py --ensaio`; `--varredura` varre sem rede);
destrutivo é do dono; furo de cerca se prova sem rodar o destrutivo; cópia
gerada não se edita; nada de segredo, nome ou caminho de máquina. O
encerramento traz o que mediu, o que derrubou, o que não conseguiu
derrubar, as linhas do quadro por identidade, e uma crítica a este prompt.

## Onde mora o SEU roteiro

Na `execucoes/` da raiz do seu repositório. Lá o conteúdo não entra no git,
de propósito: roteiro de trabalho cita o caminho da sua máquina, o nome dos
seus outros repositórios, o seu caso. Nada disso viaja.

Quando um roteiro seu deixar de citar o seu caso e passar a servir qualquer
repositório, ele é candidato a mudar para cá — e aí precisa da linha no
`.gitignore` e da seção dele em "Os roteiros, um a um", acima.
