# A guarda mecânica de cada regra

Regra que só vive em prosa depende de alguém ler sob cansaço — e é sob
cansaço que se lê errado. Esta página diz, regra a regra, **o que a cobra na
prática**: o gancho que recusa na hora, a rotina que reprova no ritual, ou
nada.

A lista das regras é `regras-da-camada.md`. Aqui não se repete o que elas
dizem; só quem as segura.

## Como esta página se refaz

Ela é medição, não opinião. Para verificar se ainda está certa:

```bash
for h in .claude/hooks/*.py; do
  printf '%-34s ' "$(basename "$h" .py)"
  grep -oE '[Rr]egra [0-9]+' "$h" | sort -u | tr '\n' ' '; echo
done
python .agents/camada/camada.py medir provar
```

O primeiro comando diz qual gancho cita qual regra; o segundo prova os
ganchos e os instrumentos — e é o que viaja. No atlas, o catálogo inteiro das
rotinas sai por `python verificacoes.py --listar`, que não viaja. Divergiu desta tabela, esta página é que está velha.

## O quadro

| Regra | Quem a cobra | Como |
| --- | --- | --- |
| 1 — abra a sessão na raiz | nada | teve gancho, o `vetar-caminho-relativo-apos-cd`, aposentado por decisão do dono: era, sozinho, a maior fonte de recusa por chamada, inclusive de comando legítimo. Ficou o conselho no briefing — caminho absoluto no argumento, ou `git -C` —, porque `cd <pasta>` seguido de caminho relativo pode fazer o cliente parar e pedir permissão. O resto da regra nunca foi mecanizável: quem abre a sessão no lugar errado não tem a camada carregada para ser avisado |
| 2 — só é pronto o que um instrumento provou | rotina `verificacao` do motor; rotina `bancada`; gancho `cobrar-apresentacao-da-entrega` | o gancho cobra na parada a entrega com interface em vizinho que declara `apresentacao` no cadastro local: mescla desta sessão na integração dele sem, depois da mescla, uma navegação ao endereço declarado pelo navegador do dono (e a narração por voz, se o cadastro pede) sai na parada com a receita, só no registro de depuração e sem segurá-la, por decisão do dono — porque para tela o instrumento que prova é o dono vendo, e prova por Playwright no shell não conta; a `verificacao` acusa veredito `segue` com `provado` vazio, e re-executa cada prova declarada; a `bancada` roda o `--testar` de cada instrumento que a sessão tocou, medido pelo git — árvore suja, arquivo recém-nascido e commit desta branch que a integração ainda não tem. Sem ela nenhuma rotina do ritual roda bancada: quem prova instrumento é a `instalada`, que está fora do ritual, e bancada vermelha fica dias sem ninguém ver. Ela prova só o que a sessão mexeu, porque a bancada inteira custa minutos — `python .agents/saude/saude.py testes` mede quanto, e a maior parte é de um instrumento só — e o ritual roda várias vezes por sessão; o que não coube no orçamento sai nomeado, com o comando que prova o resto |
| 3 — antes de criar, procure e cite | nada | **só prosa** |
| 4 — a memória mora no disco | gancho `vetar-andamento-em-arquivo`; as recusas dos ganchos de veto | o gancho recusa o arquivo de andamento nascendo com o corpo de uma issue, e nomeia a exceção: o `.md` do encerramento, em `conhecimento/`. Para o resto da regra nenhuma rotina reprova, mas **toda recusa manda gravar** o aprendizado em `conhecimento/`, com a linha concreta do que gravar — memória previne, gancho ensina |
| 5 — ao dar por pronto, faça a análise de promoção | nada | **só prosa** |
| 6 — trabalhe econômico | rotina `largada`; o instalador; cerca `vetar-enxame-de-agentes` | cobra o teto de bytes que toda sessão paga, declarado em `nucleo/configuracao.json` — e quem instala nasce com o teto medido na árvore recém-montada, escrito pelo `montar.py` na configuração com a data: o salto seguinte já é acusado, e subir o teto é decisão do dono. A regra tem uma segunda parede, contra o gasto que não é de bytes e sim de gente: a cerca conta os agentes que a sessão pôs para rodar e nega o disparo acima do `teto_de_agentes_por_sessao`. Ela conta identidade distinta, não pedido, porque agente nascido dentro do motor de roteiro nunca pede a ferramenta de subagente — só aparece quando usa alguma. A parede existe porque enxame não é profundidade: poucas perguntas viram dezenas de agentes, e o gasto deles não aparece na conta que a sessão mostra |
| 7 — rede com cortesia | nada | **só prosa** |
| 8 — segredo não entra em git nenhum | gancho `orientar-credencial`; cerca `vetar-despejo-de-ambiente`; rotina `ensaio` | o gancho intercepta leitura e shell: orienta quem lê credencial — `.env`, `.credenciais/` e as gavetas e os nomes que o Agent Governance Toolkit da Microsoft já conhecia (`~/.ssh`, `~/.aws`, `.git-credentials`, `id_rsa`, `.netrc`…) —, veta quem a entrega ao git ou ao gh, e veta a chamada ao endpoint de metadata da nuvem (`169.254.169.254`, `metadata.google.internal`), que é a credencial da máquina; a cerca recusa comando que despeja o ambiente inteiro sem nomear a variável — `env`, `printenv`, `os.environ` iterado —, porque despejo largo põe credencial no transcript, onde ninguém a apaga; o ensaio varre texto, caminho e mensagem de commit antes de publicar |
| 9 — destrutivo é do dono; commit e push | ganchos `vetar-branch-protegida`, `vetar-pergunta-ja-respondida`, `vetar-escrita-em-somente-leitura`, `vetar-comentario-explicativo` e `vetar-escrita-em-politica` | os dois primeiros leem `autorizacoes` e, sem declaração, negam; o terceiro recusa escrita em território de outra pessoa; o quarto recusa o agente editar a lista de exceções da própria cerca; o quinto recusa, durante etapa do executor, escrita nos arquivos que decidem quais cercas existem — `settings.json`, as listas que os ganchos leem, `nucleo/regras.json` e o código dos próprios ganchos — e, na mesma etapa, `curl` ou `wget` despejados num shell e `bash <(curl …)`: código baixado da rede executando sem leitura, que é o jeito de reescrever qualquer cerca por dentro |
| 10 — texto na régua | rotina `camada` | roda o validador de markdown sobre todo `.md` que o git rastreia |
| 11 — não invente passo onde já existe receita | nada | **só prosa** |
| 12 — branch de longa duração e integração contínua | ganchos `vetar-branch-protegida` e `vetar-automacao`; regra nativa de edição nos caminhos de automação, no settings de quem instala; o executor de roteiros | recusam na hora, pelo nome da branch e pelo caminho da configuração; o veto de branch recusa também o commit direto na integração e na base que `nucleo/executor.json` declara — `projetos.<nome>.branches` no vizinho, e o bloco `branches` da raiz na própria raiz, na worktree dela (achada pelo mesmo remoto `origin`) e no vizinho que não declara —; deixa passar a mescla `--no-ff` de branch de trabalho, que é o caminho da entrega, o `git merge --continue` que conclui a mescla parada em conflito e o `git commit` com `--dry-run`, `--help` ou `-h`, que não gravam; acha o cadastro do vizinho pelo nome da pasta ou pelo nome do repositório no remoto `origin`, o que cobre a worktree de vizinho com outro nome; separador dentro de aspas ou de documento literal não desliga o acompanhamento da troca de branch; vizinho sem cadastro fica como antes; o executor recusa o disparo quando a integração declarada não existe no remoto do alvo (`git ls-remote --heads origin <integração>` vazio), antes de gravar estado — sem remoto declarado não há o que medir, e ele segue calado — inclusive `.git/hooks/`, que não entra no git e roda a cada commit sem ninguém rever |
| 13 — publicar exige revisão semântica | rotina `ensaio` e cerca `vetar-documento-rastreavel`, **em parte** | a varredura acha nome e segredo; jeito de trabalhar e procedência não têm padrão e passam inteiros. A cerca fecha um buraco anterior à varredura: documento binário em caminho que o git rastreia não se lê num diff nem na varredura, e entra no commit às cegas. A parte que falta **não é mecanizável** |
| 14 — conhecimento nasce na língua de quem vai lê-lo | ganchos `vetar-conhecimento-em-codigo` e `vetar-comentario-explicativo` | os ganchos recusam a página nascendo em pasta de código e o porquê nascendo em comentário. A escolha do NOME não tem guarda mecânica, por decisão do dono: rotina que conta ocorrência de termo velho pesa em toda sessão e vive vermelha por prosa nova, sem que ninguém aja sobre o número. Ficou a regra — usar o nome que a casa já usa, não inventar jargão — e o julgamento de quem escreve |
| 15 — editou a fonte, regenere a cópia | gancho `vetar-escrita-em-copia-gerada`; regra nativa de edição no settings de quem instala; rotina `sincronia` | o gancho recusa a escrita na cópia nomeando a fonte; a regra nativa `Edit(...)` do `settings.json`, gerada pelo instalador para o espelho das skills, a regra de código, a página de regras, a automação e as cópias de módulo do registro, recusa mesmo com o gancho desligado, sem nomear a fonte (provado no cliente); a rotina regenera e compara o texto inteiro |
| 16 — nada sem destino | ganchos `cobrar-destino-da-entrega` e `vetar-escrita-fora-da-execucao`; rotina `entrega` | o primeiro cobra na parada da sessão — com gente no terminal, só no registro de depuração —, busca o remoto antes de medir a integração contra a principal, para não acusar pedido já mesclado por ref local velha, e separa a sujeira herdada (arquivo mexido antes da abertura da sessão, lida do primeiro instante do transcript) da sujeira desta sessão: a herdada é nomeada e não trava; o que não é da sessão — poda, sujeira herdada, integração herdada — sai uma vez por sessão, e a cobrança de commit mostra só o commit, sem o resto da saída da rotina `entrega`; o segundo recusa escrita fora da raiz da execução, que não entra em commit nenhum; a rotina `entrega` lista as duas pontas — o que não saiu da branch e o que já saiu e ficou: a branch contida na branch de incorporação e ainda de pé, local e remota, que se acumula porque ninguém a vê; guardar uma delas é declará-la em `.claude/branches-protegidas.txt`. As três guardas olham para o disco e para o git; nenhuma vê o rastreador, e issue vizinha que fala do mesmo trabalho sem apontar para a que o consolidou fica sem guarda mecânica |
| 17 — explique na altura de quem lê | nada | **não mecanizável**: altura de explicação não se mede por padrão |
| 18 — número não mora em prosa | nada | **só prosa**; mecanizável em parte: uma rotina pode varrer as páginas por algarismo solto em prosa, sem comando nem data ao lado, e acusar — ninguém a escreveu |
| 19 — não pare sem necessidade | nada | **não mecanizável**: necessidade de parar é julgamento sobre o trabalho, não padrão |
| 20 — decisão do dono não se reabre sem citar a data e o motivo | nada | **não mecanizável**: reabrir decisão é sentido, não padrão; a trava é o próprio dono, que lê a proposta e cobra a data e o fato novo |

## Negar ou perguntar: o verbo de cada veto

Um gancho que veta responde com um de dois verbos. `deny` recusa na hora,
sem consultar ninguém. `ask` manda a chamada para o prompt de permissão do
Claude Code: o dono lê a razão do gancho e decide, e a sessão espera. Os
dois são nativos do evento `PreToolUse` — o gancho escolhe um no campo
`permissionDecision` e explica em `permissionDecisionReason`. O desenho é o
mesmo do Agent Governance Toolkit da Microsoft, citado mais abaixo: lá,
exigir aprovação é exatamente um `ask` em gancho `PreToolUse`.

**Quem pergunta e quem nega — decisão do dono.** Perguntam
os vetos de julgamento, em que a recusa é opinião sobre o trabalho
e o dono presente pode discordar — a lista sai da constante
`DECISAO_DE_PERGUNTAR` no código de cada gancho:

- `vetar-andamento-em-arquivo`
- `vetar-comentario-explicativo`
- `vetar-conhecimento-em-codigo`
- `vetar-despejo-de-ambiente`

**Não seguram, com gente no terminal — decisão do dono.** Motivo: os dois
leem prosa ou estado de árvore compartilhada, erram para o lado de segurar
quem estava certo, e o portão que de fato segura entrega é do servidor. Com
gente, o primeiro avisa na conversa e o segundo só grava no registro de
depuração, como diz o parágrafo seguinte. Sem ninguém no terminal os dois
continuam fechando a porta: o primeiro nega, o segundo bloqueia a etapa do
executor.

- `vetar-pergunta-ja-respondida`
- `cobrar-destino-da-entrega`

**Com gente, a cobrança de parada não fala com ninguém — decisão do dono.**
Com gente no terminal, `cobrar-destino-da-entrega` e
`cobrar-apresentacao-da-entrega` escrevem a cobrança como saída comum do
gancho, em texto que não é JSON, e saem com código 0. Para a parada, a
documentação do cliente manda essa saída para o registro de depuração, não
para a conversa nem para a tela. Por isso a sessão não espera ver a
cobrança. Antes de encerrar, ela prova o destino com
`python .agents/camada/camada.py --entrega`, `git status` em cada
repositório tocado e os critérios da issue: o `--entrega` não mede árvore
suja, vizinho tocado sem destino, critério de pronto em branco nem pedido
sem revisor, que o gancho mede.
Sem ninguém no terminal nada mudou, e o destino segue bloqueando a etapa do
executor. A cerca `vetar-pergunta-ja-respondida` avisa antes da ferramenta,
não na parada, e o aviso dela segue na conversa.

Negam de vez os que protegem o que não se desfaz — branch de longa
duração, política, território de outra pessoa, cópia gerada, automação, a
fronteira da execução, o documento rastreável e a sessão de pesquisa:

- `vetar-automacao`
- `vetar-branch-protegida`
- `vetar-documento-rastreavel`
- `vetar-escrita-em-copia-gerada`
- `vetar-escrita-em-politica`
- `vetar-escrita-em-sessao-de-pesquisa`
- `vetar-enxame-de-agentes`
- `vetar-escrita-em-somente-leitura`
- `vetar-escrita-fora-da-execucao`

O julgamento de cada veto não mudou: o que barrava continua barrando.
Mudou quem dá a última palavra em sessão interativa.

**Nome lido em texto cru só avisa.** Quando o destino da escrita está em
variável, as cercas de somente leitura e de cópia gerada não têm caminho para
julgar, e o que resta é achar o nome protegido no texto do comando. Isso é
adivinhar, e por isso sai como contexto para o modelo, sem recusa. A
exceção é operação reconhecida: `git` ou `gh` que escreve, com o diretório em
variável e o vizinho somente leitura nomeado no comando, continua negado.

**Sem ninguém no terminal, todos negam.** O executor de roteiros põe a
marca `ENCADEADOR_ETAPA` no ambiente de cada etapa, e é ela o sinal de que
ninguém responde: ali um `ask` ficaria sem resposta. Com a marca, os vetos
que perguntam respondem `deny`, com a mesma razão. O modo de permissão não
serve de sinal: ele não diz se há gente presente, e `bypassPermissions` roda
também com alguém no terminal. A decisão que precisa do dono continua parando a
execução pelo desenho de sempre — veredito de pergunta na evidência,
execução em `aguardando-resposta`, resposta pela retomada. O verbo `ask`
não muda esse desenho; ele só encurta o caminho quando há alguém na frente
do terminal.

**Em `bypassPermissions` com gente — decisão do dono.** Esse modo desliga
as perguntas de permissão, e a documentação do cliente não garante que a
pergunta de um gancho apareça nele. Por isso os vetos que perguntam negam
também nesse modo: é o único jeito de a regra valer. A cerca
`vetar-pergunta-ja-respondida` só avisa nele, como nos outros modos: a
pergunta é ela mesma o caminho até o dono, e a cerca a lê por padrão de
texto, então negar ali barraria qualquer pergunta que só citasse commit.

Para saber quem pergunta, pergunte ao código, não a esta página:

```bash
grep -l DECISAO_DE_PERGUNTAR .claude/hooks/vetar-*.py
```

## O que este quadro ensina

**As regras sem guarda nenhuma são as que o quadro marca com `nada`** —
hoje 1, 3, 5, 7, 11, 17, 18, 19 e 20. A conta sai do quadro, nunca desta
prosa:

```bash
grep -cE '^\| [0-9]+ [^|]*\| nada \|' conhecimento/guarda-mecanica-das-regras.md
```

Três delas (17, 19 e 20) não são mecanizáveis pelo que são — altura de
explicação, necessidade de parar e reabertura de decisão são julgamento,
não padrão. As outras são candidatas, e a candidata mais barata é
sempre a que já tem instrumento e não tem quem o chame. A regra 1 já teve
gancho e voltou a esta lista quando ele foi aposentado: guarda que recusa
mais do que protege custa mais que a falta dela.

**A regra 4 tem guarda de um lado só.** O item do estado do trabalho tem
gancho: o `vetar-andamento-em-arquivo` recusa o arquivo que
nasce com o corpo de uma issue, porque a regra já vivia em três prosas — os
dois prompts de abertura e a skill `trabalho-por-issue` — e uma instalação a
atravessou assim mesmo. Guarda por prompt é mais fraca que guarda por rotina,
e este é o caso que provou.

Do outro lado, nada reprova a sessão que não grava o aprendizado. O que existe
é toda recusa mandar gravar, com a linha pronta: memória previne, gancho
ensina.

**Guarda mecânica não é tudo.** A classe de erro que nenhum gancho pega é
outra: **interpretar errado um texto lido corretamente**. Foi o que aconteceu
quando uma regra geral atropelou um procedimento específico e nada acusou o
conflito — as duas frases estavam certas, e a leitura é que escolheu a errada.
Para essa classe a trava é revisão adversarial, não gancho: alguém, ou alguma
etapa, pergunta *por que não o contrário?* antes de a decisão virar ação.

**Nada fica sem destino.** A cobrança da regra 16 é sobre a branch de
entrega **e** o passo seguinte: ou o trabalho vai para lá com o pedido de
incorporação ABERTO, ou é descartado com a razão dita em uma linha.
Trabalho parado antes disso não chegou a lugar nenhum, só parece pronto —
mesmo que o commit já esteja na branch certa.

**A cobrança pode nomear um PR que já fechou.** O gancho lê o estado local
sem `git fetch` antes — se o dono mesclou o pedido de incorporação segundos
antes de a sessão encerrar, a lista de commits que ele imprime já está
resolvida no GitHub. Confira com `gh pr view <número> --json state` e
`git fetch origin && git log --oneline origin/main..origin/homolog` antes de
abrir um PR novo: `state: MERGED` e 0 commits de diferença fecham o caso sem
nenhuma ação — não é um alarme falso do gancho, é uma corrida entre a
mesclagem e a leitura.

**Guarda nova se prova duas vezes: na suíte, e contra o repositório de
verdade.** Suíte verde não é prova de que a guarda funciona — o cenário de
mentira só contém os casos que quem escreveu imaginou. Uma rotina que acusa
branch entregue e não podada passou na própria suíte com três defeitos que
só a população real mostrou.

- **O erro virou acusação falsa.** O `--format` do `git branch` leva
  parênteses, que o shell quebra; e como o auxiliar que roda comando devolve
  a saída padrão e a de erro **juntas**, o texto do erro entrou na lista como
  se fosse nome de branch. Engolir erro em volta de uma medição já transforma
  falha em número; em volta de uma **acusação**, é pior — inventa acusado.
  Falha vira "não medido", nunca lista.
- **O ponteiro do remoto virou branch.** `origin/HEAD` encurta para o nome do
  remoto, sem barra, e entrou como mais uma — pondo um nome errado no comando
  que a rotina mandava rodar.
- **O critério óbvio errava nas duas direções.** "Está contida na branch de
  incorporação" deixava passar a branch cujo topo é um nó de mescla nunca
  mesclado adiante, embora todos os pais dele já estivessem lá, e acusava a
  branch recém-criada, que ainda não tem rastro nenhum. O critério que
  fecha é **não acrescentar nada** ao destino, mais a comparação de topo — e
  ele fecha até onde o git deixa: a branch recém-criada só é isenta quando
  nasce do topo da incorporação. Cortada de um ponto anterior, ela é acusada,
  porque o git não guarda em que branch um commit nasceu: a que foi entregue e
  a que acabou de sair de um ponto antigo apontam, as duas, para um commit que
  já está no destino. Contar commits próprios não separa uma da outra —
  medido: dá zero nos dois casos —, e por isso o limite fica declarado aqui e
  preso por um caso na suíte, em vez de ser "consertado" com um critério que
  deixaria a branch entregue passar.

A regra que sai daí: **guarda que acusa precisa de população real antes de
alguém dizer que ela funciona** — e o caso de controle, aquele que ela NÃO
pode acusar, entra na suíte junto com os que ela deve.

**Regra madura de fora entra copiada, não instalada.** Os ganchos
ganharam as regras de segurança do Agent Governance Toolkit da
Microsoft (MIT, `agent-governance-claude-code/config/default-policy.json`
em <https://github.com/microsoft/agent-governance-toolkit>) que ainda não
tinham, cada uma no gancho que já cobria a regra da camada em que ela cai:
os nomes e as gavetas de credencial e o endpoint de metadata da nuvem no
`orientar-credencial` (regra 8); código baixado da rede executando sem
leitura no `vetar-escrita-em-politica` (regra 9); e `.git/hooks/` no
`vetar-automacao` (regra 12). O verbo é o de cada gancho, não o do
plugin: ler credencial continua orientando, porque ler localmente é livre;
código baixado da rede só é recusado durante etapa do executor, porque em
sessão interativa o prompt de permissão é a revisão, e essa cerca só se
levanta na etapa, onde não há quem responda um `ask`; e das escritas que
lá só pedem revisão — rc de shell, `.git/hooks/`, `package.json` — entrou
a única que revisão nenhuma alcança, `.git/hooks/`, que o git não mostra.
Ficaram de fora, de propósito: o veto geral a `rm -rf`, porque a regra 9
já cerca o destrutivo por caminho e `tmp/` se apaga sem perder nada; e o
veto a despejar o ambiente (`env`, `printenv`), porque é leitura local,
sem caminho que ancore o veto de entrega — esse entrou depois, como
`vetar-despejo-de-ambiente`, por outro motivo: não o
caminho, mas o transcript, onde o despejo largo deixa a credencial sem
ninguém para apagá-la. Instalar o plugin custaria Node,
um processo por chamada e contexto em inglês em toda sessão — a licença
existe para levar a regra e deixar o peso.
