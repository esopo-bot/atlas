# Mudanças da camada

Cada versão, pelo efeito que você vê. O número aparece em todo comando
(`python montar.py --versao`); máquina com número menor está atrasada.

## 0.88 — 2026-08-17

O encadeador entrega as regras por código, e a corrente ganha a página que
ensina a usá-la.

### Mudado

- **Toda etapa de sessão da corrente recebe as regras na frente do prompt.**
  O encadeador lê `conhecimento/regras.json` e injeta as frases imperativas,
  citadas (`> `), antes da configuração da casa e do pedido — entrega
  determinística, a lição medida no sistema estudado: regra dura que depende
  de o modelo lembrar de buscar falha no pior dia. Fonte ausente é silêncio;
  ilegível avisa e segue — nenhuma etapa derruba a corrente por causa de
  aviso. Quatro casos novos no `--testar` (53).
- **`fluxos/rodar-uma-corrente.md`: o motor ganha o passo a passo.** A
  esteira de recibos existia com autoteste e batismo em produção, e o
  desenho morava só em docstring — quem não abre `.py` não sabia usar.
  Cartão de bolso: manifesto mínimo, os quatro tipos de etapa, ensaio,
  execução, leitura de recibo e os limites confessados. Entra no menu, no
  mapa e no LEIAME de fluxos — o endereço de chegada da regra da 0.84.

## 0.87 — 2026-08-17

A regra vira dado: a fonte é JSON, a página é gerada, e instrumento confere.

### Mudado

- **As regras da camada ganham fonte em `conhecimento/regras.json`.** Decisão
  do dono: regra em parágrafo esconde a ordem no meio da história — quem lê
  garimpa em vez de obedecer. Cada regra agora é id estável, frase imperativa
  e itens curtos; o porquê e as medições ficam nas páginas de procedência
  linkadas (zero que mente, ganchos, mapa), onde a história sempre morou.
  Conteúdo nenhum se perdeu — mudou o endereço dele.
- **`regras-da-camada.md` passa a ser GERADA.** O `--sincronizar` gera a
  página da fonte antes de embutir, com a marca de gerada no topo; fonte
  inválida derruba a sincronização — regra quebrada que passasse calada
  viraria lei quebrada em toda casa que atualizar. A fonte viaja no FONTES:
  a casa de destino recebe o dado junto com a página, e código dela pode ler
  as regras como dado (warm-up de corrente, gancho, subagente).
- **`zero-que-mente.md` ganha o bolso.** Tabela causa → hábito no topo, uma
  linha por causa: a página se abre no meio do incidente, e incidente não
  tem tempo para 250 linhas. As seções viram a prova de cada linha.
- O verificador local confere fonte × página (ids sem furo, toda regra
  presente, marca de gerada) — o segundo consumidor do dado.

## 0.86 — 2026-08-17

A página de abrir e fechar vira cartão de bolso, o mapa mostra a esteira que
já morava na camada, e a issue deixa de carregar convenção de uma casa só.

### Mudado

- **`abrir-e-fechar-a-sessao.md` reorganizada como cartão de bolso.** Os
  três blocos coláveis — partida, auditoria, esfriamento — vêm primeiro, na
  ordem em que o dia os usa; o porquê de cada um desce para uma seção única
  de leitura de uma vez. Nenhum bloco mudou de conteúdo — só a ordem da
  página, que é a mais aberta da camada.
- **A árvore do mapa ganha o que faltava.** `.agents/recibo/` e
  `.agents/conferir/` viajam com a camada desde a 0.78 e não apareciam no
  mapa que o `AGENTS.md` promete completo; entram também `ambiente.txt` e
  `site/`. A esteira deixou de ser invisível para quem só lê o guia.
- **`historia-em-issue.md` devolve nome e fila à configuração.** O padrão
  `semana_N_hist_M` era citado como regra universal; era convenção de uma
  casa vazando para a camada pública. Agora nome e ordem de entrada moram
  no `configuracao-da-casa.md`, como a skill `trabalho-por-issue` já fazia
  — a autoridade fica uma só, e o exemplo continua na página como exemplo.
- **O canivete confere a tabela de fábrica contra sessão real.** Quatro
  comandos citados não existiam na conferência de 17/08/2026 e saíram; a
  tabela agora carrega a data da última conferência.
- **`fluxos/LEIAME.md` para de prometer fluxos que a camada tirou.** A linha
  de exemplos citava refatoração, migração e entrega — removidos de
  propósito na 0.59; agora lista o que existe.
- **Encadeador: o aviso do teto vira comportamento testado.** O caso do
  `configuracao-da-casa.md` acima do teto passou a capturar o stderr e
  provar que o aviso sai — antes o aviso vazava no meio da saída do
  `--testar` com cara de defeito. E a conferência perdeu um
  `CompletedProcess` fake que embrulhava valores já computados — vestígio de
  desenho antigo, mesma semântica, leitura direta. Os 49 casos seguem
  passando.

## 0.85 — 2026-08-17

O zero que mente ganha a causa da identidade errada, e a regra do segredo
passa a cobrir a porta por onde nenhum instrumento olha: a tela.

### Mudado

- **`zero-que-mente.md` ganha a causa 9: quem perguntou não foi você.**
  Ferramenta com sessão ativa responde pela identidade do momento, não pela
  que você tem em mente — e "não existe" é a resposta honesta para a conta
  errada. Medido em 17/08/2026 com a conta de publicação ativa por engano:
  consulta ao repositório deu `404`, `git pull` deu `Repository not found`, e
  a contraprova fechou porque os mesmos comandos funcionaram com a conta
  certa. O `404` é de propósito: dizer "sem permissão" confirmaria a
  existência a quem não deveria saber dela. Três hábitos, e o do meio é o que
  quase ninguém tem: **pergunte ao token, não ao rótulo** — o comando que lê
  a configuração guardada devolve o nome anotado ali, e o token em uso pode
  ser de outra conta. Fecha com as duas exigências de um portão de
  identidade, as três medidas no mesmo incidente de provedor: prova única é
  ponto único de falha (a rota do usuário deu `503` com o resto da interface
  de pé, e o trabalho parou com tudo verde à volta); **uma tentativa só
  desperdiça a reserva** (oito amostras por rota — a morta deu 0/8 e a
  reserva 5/8, viva porém intermitente, e um portão que tenta cada prova uma
  vez para em um terço das execuções acusando credencial que está boa); e
  qual das provas respondeu aparece na tela. Fecha com a armadilha de leitura
  que apareceu no caminho: amostra única mentiu duas vezes no mesmo minuto —
  quando o resultado for intermitente, conte, não conclua da primeira.
- **A regra 8 passa a cobrir a tela.** Print, janela compartilhada e captura
  de erro levam credencial para dentro do contexto sem passar por gancho,
  permissão ou varredura — **instrumento nenhum vê imagem**. Todos os da
  camada julgam caminho de texto. Antes de mandar um print, feche o que
  estiver aberto com segredo.
- **`ganchos.md` declara o limite no lugar onde se procura por ele.** A lista
  de limites do professor de credencial ganha "ele não vê imagem": não existe
  chamada de ferramenta para interceptar um print. É a mesma mudança em dois
  endereços, como a regra do endereço de chegada da 0.84 pede — quem lê a
  regra 8 encontra o princípio, quem investiga o gancho encontra o buraco.

## 0.84 — 2026-08-17

O conhecimento ganha a regra do endereço de chegada, a página de MCP aprende
o servidor que sobe sem as variáveis que usa, e o território do perfil do
sistema confessa que falha sem mudar de máquina.

### Mudado

- **`mapa-do-repositorio.md` ganha "Toda página nasce com endereço de
  chegada".** Conhecimento sem endereço não existe para quem precisa dele:
  página entra com dois caminhos — a linha no índice **e** o link vindo de
  onde a necessidade nasce —, regra geral carrega o endereço das suas
  exceções, e na poda a página sem link de entrada sai por definição, não por
  opinião. A lista de arrumação já cobrava o link de entrada e não tinha
  regra para citar; agora tem. E a skill `analise-de-promocao` aponta para a
  regra no momento em que a necessidade nasce — ao propor página nova.
- **`mcp.md` ganha o quarto modo de falha.** Servidor declarado sem as
  variáveis que usa **sobe do mesmo jeito**, aparece na lista de ferramentas
  e só falha na primeira chamada — engana no sentido oposto aos outros três,
  porque tudo parece vivo até o uso. Medido com sonda em 17/08/2026: sem a
  variável, o `initialize` respondeu, o `tools/list` trouxe a ferramenta, o
  processo seguiu vivo e o erro só apareceu no `tools/call`. O conserto é
  declarar o nome onde algum instrumento o leia — `${VARIAVEL}` na própria
  declaração ou `variavel NOME` no `ambiente.txt`.
- **`estado-que-nao-viaja.md`: o território 4 falha sem mudar de máquina.**
  Processo nascido de outro pai — aplicativo aberto pelo ícone, serviço,
  agendador — não herda o que o perfil do shell exporta. A lição inteira
  continua numa casa só, a página de MCP.
- **`ganchos.md` ensina a distinguir quem te barrou.** Regra do
  `settings.json` nega curto e sem lição; gancho nega ou orienta com a lição
  no próprio texto.

## 0.83 — 2026-08-17

O professor de credencial aprende a segunda porta e o subcomando do git, o
muro da gaveta sai de onde o professor alcança, e o publicador de tokens
aprende o canal que a sessão gráfica lê.

### Mudado

- **`orientar-credencial.py` julga o subcomando do `git`, não o nome.**
  `git ls-files`, `git status` e `git check-ignore` sobre a gaveta calam
  (leem nome); `git log`, `git diff`, `git show` e `git grep` orientam
  (leem conteúdo); todo o resto — `add`, `commit`, `stash`, o que vier —
  continua vetando. O motivo é falso positivo medido em 17/08/2026: uma
  sessão de diagnóstico barrada de perguntar ao git o que estava
  versionado, por comandos que não escrevem nada. Suíte: 65 casos — 24
  orientam, 8 vetam, 33 calam.
- **O professor cobre a leitura direta (`Read`), e o muro da gaveta cai.**
  O `deny` de `.credenciais/**` barrava sem lição até script versionado que
  mora na gaveta; agora o gancho atende as duas portas (matcher
  `Bash|PowerShell|Read`, avaliador `--avaliar-arquivo`), leitura direta
  nunca veta — ler não publica — e a atualização migra o `settings.json`
  das casas que já têm a camada. Os padrões que são segredo por definição
  (`.env*`, `appsettings*`) continuam negados. **No Devin o muro fica**:
  ferramenta sem gancho não tem professor, e muro só sai de onde chegou
  instrumento melhor.
- **`publicar-mcp-env.py` publica no canal que o sistema lê.** Medido em
  17/08/2026: variável publicada só para o shell não chega ao aplicativo
  aberto pelo ícone — a sessão gráfica não lê o perfil do shell, e o
  servidor MCP morre em silêncio com o `mcp.env` perfeito. No Linux com
  systemd o publicador agora escreve um drop-in em
  `~/.config/environment.d/` (modo 600, valor nunca na tela); no Windows
  segue o `setx`; sistema fora dos dois medidos recebe a confissão, não um
  chute. A lição está na página de MCP. **A cópia que já existe no
  workspace não é trocada pela atualização** — o esqueleto preserva o que
  existe; copie a versão nova por cima quando quiser o conserto.

## 0.82 — 2026-08-17

O professor de credencial aprende que atribuição de ambiente é
configuração, e a página do zero ganha a causa do filtro que você mesmo
escreveu. (A revisão semântica pré-publicação cobrou o anonimato da casa
no meio da rodada e o número andou junto — não existe 0.81 publicada.)

### Mudado

- **`orientar-credencial.py` cala em atribuição de ambiente literal.**
  `GH_CONFIG_DIR=.credenciais/.gh-bot gh pr create` autentica pelo chaveiro
  e publica só o corpo — o veto aqui era falso positivo, medido em
  17/08/2026 barrando o PR de promoção da própria casa. Atribuição com
  `$( )` continua na varredura (lê de verdade → orienta), e credencial no
  argv do verbo continua vetando. Suíte: 54 casos — 20 orientam, 6 vetam,
  28 calam.
- **`zero-que-mente.md` ganha a causa 8:** o filtro que você mesmo escreveu
  esconde a resposta — excluir um termo por conteúdo some com as linhas que
  o citam (medido duas vezes no mesmo dia) — e o primo dela, o zero falso
  de frase procurada em prosa formatada.

## 0.80 — 2026-08-16

A trava de credencial vira professor, a montagem passa a conferir o índice
do git, e a casa ganha um lugar para dizer onde as issues nascem. (A rodada
passou por refutação adversarial no meio: os consertos que ela cobrou estão
na lista, e o número andou junto — não existe 0.79 publicada.)

### Mudado

- **`vetar-credencial.py` virou `orientar-credencial.py`.** Ler credencial
  pelo shell deixa de ser negado: o comando passa e o modelo recebe a lição
  junto (`additionalContext` — medido: chega ao modelo sem mexer no fluxo
  de permissão). O veto continua **só no que não se desfaz**: alvo de
  credencial indo para `git`/`gh` (commit, comment, pr). A atualização
  migra o `settings.json` e remove o arquivo antigo; teste com 49 casos —
  19 orientam, 5 vetam, 25 calam.
- **O gancho é o primeiro cliente do recibo da esteira:** cada orientação
  materializa um recibo `segue` e cada veto um `para`, por código
  (`.agents/recibo/`), em `tmp/recibos/` — com prova re-executável
  (`--avaliar`).
- **A conferência do fim da montagem pergunta também ao índice do git.**
  Antes ela só perguntava ao ignore, e arquivo criado mas nunca adicionado
  passava como "em dia" — foi assim que um gancho ficou fora do git sem
  ninguém ver. Agora: ignorado é um aviso, fora do índice é outro.

### Adicionado

- **Molde `configuracao-da-casa.md`** na raiz: onde as issues desta casa
  nascem, padrão de nome e fluxo do backlog. A camada cria o molde
  (montagem e atualização); o valor é seu e nunca é sobrescrito. A skill
  `trabalho-por-issue` lê antes de criar issue, e o módulo `encadeador`
  entrega o arquivo no prompt de toda etapa de sessão — com três cuidados
  refutados antes de escritos: arquivo com UTF-8 quebrado (editor de
  Windows salva cp1252) segue com o prompt puro em vez de derrubar a
  corrente sem recibo; as linhas entram citadas (`> `), para config que
  imita a moldura não fabricar limite falso; e acima de 64 mil caracteres o
  prompt segue sem ela, com aviso — config de casa é uma página.
- **As regras de fila em página:** `fluxos/historia-em-issue.md` ganhou "A
  fila e o nome" — nome `semana_<ISO>_hist_<n>`, nasce no backlog, achado
  novo entra na próxima hist, uma sessão termina um trabalho.

## 0.74 a 0.78 — 2026-08-16 (registradas em atraso)

A esteira de recibos chegou em cinco degraus e estas entradas não foram
escritas na hora: **0.74** o contrato e o escritor de recibo
(`.agents/recibo/`, recibo materializado só por código); **0.75** a
conferência (`.agents/conferir/`, re-executa cada prova e acusa
divergência); **0.76** o módulo opcional `encadeador` (manifesto com
dependências, fork/join, ensaio-sentinela); **0.77–0.78** os consertos que
o primeiro uso real cobrou (a conferência herda o ambiente das etapas e
confere só a execução corrente; prova de git ancora em SHA; logs por
ciclo).

## 0.73 — 2026-08-16

A trava de credencial para de ser punitiva. Ela barrava pelo alvo e ignorava
o verbo — então `test -d .credenciais`, `ls` e `grep` que só citavam o
caminho caíam junto com `cat .env`, e organizar o cofre virava briga com a
própria proteção (o defeito que a issue #22 já tinha anotado).

### Mudado

- **A trava agora pergunta duas coisas, não uma: o alvo é credencial E o
  comando lê o conteúdo?** Ler NOME/existência passa (`ls`, `test`, `find`,
  `stat` — allowlist curto e conferível); ler CONTEÚDO continua barrado
  (`cat`, `less`, `grep` dentro, `cp`, `python -c open`, substituição de
  comando). O julgamento é por segmento: `ls .credenciais && cat .env` barra
  pelo `cat`, e o `ls` do lado não o inocenta. Errar no allowlist sobra em
  falso positivo, nunca em vazamento. O teste subiu de 33 para 45 casos.

## 0.72 — 2026-08-16

A camada aprende com a mudança de máquina. Uma migração real de disco provou
o padrão: o que mora no git chega inteiro; o que mora fora — variável,
perfil de CLI, ferramenta, estado da própria ferramenta de agente — morre em
silêncio, e cada peça para dias depois com cara de defeito novo.

### Adicionado

- **Página "o estado que não viaja"** (`conhecimento/`): os quatro
  territórios do estado, a regra de bolso — o que vale amanhã mora no git;
  o que a sessão precisa e não está nele se declara por nome e se confere
  por instrumento — e o padrão da página de máquina nova.
- **Fluxo "mudar de máquina"** (`fluxos/`): o antes e o depois da mudança,
  e os sintomas que denunciam migração malfeita.
- **Gancho `conferir-ambiente.py`** (`SessionStart`): acusa na abertura o
  que a máquina não tem e a casa declara precisar — as variáveis `${VAR}`
  do `.mcp.json` e o que o `ambiente.txt` da raiz declarar (comando, pasta,
  arquivo, variável). Nomes e existência, nunca valores; cala quando está
  tudo lá. O `ambiente.txt` é do dono, como a lista de branches protegidas:
  a atualização conserta o código e nunca reescreve a declaração.

## 0.71 — 2026-08-15

A regra 9 para de calar sobre commit. Ela mandava conferir a autorização da
casa antes de empurrar e não dizia nada sobre gravar — e silêncio, para um
agente, é autorização.

### Mudado

- **Commit e push passam a andar juntos na regra 9.** A mesma assimetria já
  tinha sido corrigida na 0.70, no modelo que nasce em repositório novo, e
  ficou de pé na lista numerada: o mesmo fato em duas casas, dizendo coisas
  diferentes. Agora as duas falam igual — e nenhuma decide pela casa de
  ninguém, porque a permissão continua sendo de cada repositório, gravada no
  perfil dele.

## 0.70 — 2026-08-15

A camada ganha a segunda trava dura, e a primeira para de vazar. Até aqui a
única proteção que um instrumento sustentava era a das branches de longa
duração — e ela deixava passar cinco comandos destrutivos, medidos. O resto
era prosa: texto que pede e não impede. Esta versão fecha os dois lados.

### Adicionado

- **Credencial não se abre por comando de shell.** A regra de `deny` das
  permissões cobre a ferramenta de leitura de arquivo, e só ela: pelo
  terminal, `cat .env` passava inteiro. O gancho novo olha o **alvo** do
  comando, nunca o verbo — `cat`, `less`, `grep`, `Get-Content` e
  `python -c open(...)` abrem arquivo do mesmo jeito, e listar verbos é
  corrida perdida. Ele carrega o próprio teste: `OK: 33 casos — 17 barrados,
  16 liberados`. Metade da lista existe para provar que ele não atrapalha:
  falar do assunto passa, e só o que executa é recusado.
- **Ele não substitui a regra de permissão.** Gancho falha aberto, então o
  `deny` continua como rede de baixo. É sobreposição declarada, não descuido
  — e está escrito na página de ganchos, junto dos outros três limites.

### Mudado

- **O veto de branch protegida parou de vazar em cinco lugares.** Comando em
  várias linhas, nome de branch entre aspas, `push origin --delete`,
  `push --mirror` e substituição por `$(...)` devolviam "sem motivo para
  recusar" — todos medidos. Agora barram. De `29 casos — 16 barrados, 13
  liberados` para `45 casos — 24 barrados, 21 liberados`, e **cada caso novo
  que barra ganhou um par que passa**: veto largo demais é desligado na
  primeira semana.
- **Cada regra passa a ter uma casa só.** Três arquivos diziam coisas
  diferentes sobre quem commita e quem empurra. Agora o `AGENTS.md` é a única
  casa dessa regra, e os outros apontam para ela em vez de repetir. É a
  barreira contra fato duplicado aplicada ao próprio guia: repetido em dois
  lugares, ele envelhece torto e passa a mentir de um dos lados.
- **O modelo que nasce em repositório novo passa a falar de commit.** Ele
  dizia o que fazer com push e calava sobre gravar — e silêncio, para um
  agente, é autorização. A frase nova não decide pela casa de ninguém:
  devolve a decisão ao repositório de destino, como já fazia com push.

## 0.67 — 2026-08-14

Os modos de falha do instrumento, vindos de uma sessão de investigação
noutra casa. Onze candidatos, sete entram — e o melhor deles não estava na
lista: era o que a proposta de promoção revelou sobre a própria skill que a
escreveu. O custo fixo por sessão não se moveu: 74.

### Adicionado

- **A promoção confere o endereço antes de propô-lo**
  (`analise-de-promocao`). A proposta que originou esta versão mandava a
  lição para uma skill enquanto a página que já trata do assunto estava no
  disco daquela mesma casa. Promoção sem conferir a casa existente abre a
  segunda versão do mesmo fato — e duas versões envelhecem torto.
- **Causa 7 no zero que mente: a medição saiu de outro lugar.** O diretório
  de trabalho persiste entre chamadas em várias ferramentas; um `cd` muda o
  chão de todas as seguintes. Medido em três chamadas: a mesma contagem deu
  11 na subpasta e 7 na raiz. A perigosa é a do meio — número plausível, do
  lugar errado.
- **A causa 6 ganhou o tempo**: conferência que depende de evento não fecha
  em janela sem evento. Zero honesto de uma hora sem movimento se lê como
  veredito. Ache o gatilho antes de prometer a conferência.

### Mudado

- **A regra 2 separa o negativo do provado.** Zero, vazio e "sem permissão"
  são a mesma tela para "o fato não existe" e "o instrumento não o
  enxerga"; vira prova só depois que o mesmo instrumento, na mesma janela,
  achar alguma coisa. Sem contraprova, escreve-se **não medido**.
- **A regra 8 diz que endereço não é segredo.** Domínio, região ou nome de
  fila que só existam dentro do arquivo de credencial ficam invisíveis: a
  sessão não abre o arquivo, e para. O que ela precisa para medir se
  escreve onde ela lê.
- **O zero que mente vale para todo instrumento**, não só para busca —
  consulta de registro, chamada de interface e verificação de permissão
  entram na abertura e na regra de uma linha.
- **A investigação reproduz a chamada do cliente real** (passo 1): uma
  opção a mais na sua — credencial, cabeçalho, sinalizador — percorre outro
  caminho e fabrica um defeito que não existe. Defeito fabricado parece
  achado.
- **O perfil guarda o durável; a nota, o volátil** (`wiki-de-projetos`).
  Formato de registro, permissão e endereço de ambiente mudam toda semana:
  perfil que os absorve parece desatualizado a cada rodada.

## 0.66 — 2026-08-11

Sete lições de uma semana de trabalho real, triadas pelo portão: nove
candidatas, duas rejeitadas na barreira. O custo fixo não se moveu: 74.

### Adicionado

- **Causa 6 no zero que mente: ambiente sem massa.** Tela zerada onde o
  dado nunca existiu não prova nada; "o dado existe aqui?" custa uma
  consulta direta. E remendo de massa feito por fora morre na próxima
  recriação do ambiente — o conserto durável mora no que recria.

### Mudado

- **A regra 2 fecha a taxonomia da prova**: executado com saída vista é
  prova; documentado com endereço é citação; fluxo que ninguém executou
  nem tem fonte citada é hipótese — e se grava marcado como hipótese.
- **A regra 9 classifica o redesenho**: mudança de experiência é decisão
  do dono — esboço e pergunta fechada antes do código; conserto de
  defeito não pede.
- **A causa 5 ganhou o papel**: presença em interface se prova navegando
  com o papel de quem vai usar — o portão de acesso é parte do caminho.
- **A promoção confere o corpo do pedido de revisão**
  (`trabalho-por-issue`): o que o diff tem e o corpo não conta, o revisor
  aprova sem ver.
- **O cético ganhou a fronteira da casa**: conclusão que vai sair —
  e-mail, pedido de revisão, mensagem a terceiro — passa pelo cético
  antes. Descrição intocada; o retoque é no corpo.
- **O esfriamento confere o que ficou para trás**: repositório tocado com
  commit fora da branch que o entrega — inclusive o do próprio workspace,
  que ninguém trata como trabalho — se relata no fechamento.

## 0.65 — 2026-08-09

O pacote de cortes da auditoria. A camada faz o mesmo custando menos.
(A 0.64 foi um sincronizar intermediário desta mesma leva, sem commit.)

### Mudado

- **O custo fixo por sessão caiu de 81 para 74 linhas.** A `qualidade`
  encolheu de 30 para 20 (o corpo injetado, de 25 para 16) sem perder
  decisão. O `AGENTS.md` do atlas ganhou o ponteiro para a lista de
  regras — a segunda porta que a 0.62 deu aos destinos e esqueceu na
  origem — e pagou parte do acréscimo cortando o que o mapa e o LEIAME
  de módulos já entregam.
- **O guia caiu de 1521 para 1439 linhas**, já contando as seções novas
  da 0.63: `mcp.md` −38 (a cortesia de rede tem casa na regra 7; o que
  reescrevia doc oficial virou endereço + síntese), `ganchos.md` −12,
  mapa −14, `comece-aqui` e fluxos enxutos. O prompt da partida encolheu
  de ~1280 para ~700 caracteres — as nuances que só existiam nele
  ("saída colada é citação, não prova"; "uma por vez, com a recomendação
  primeiro") subiram para as regras 2 e 9, que são a casa.
- **Molde que só a abertura usa desceu para `references/`** em três
  skills: trabalho-por-issue 234→179, documentar-processo 99→74,
  wiki-de-projetos 97→81. No corpo, que carrega em todo disparo, ficou a
  regra; o molde carrega só quando se abre.
- **O módulo observabilidade perdeu 45 linhas de duplicação em
  lockstep** — tabela repetida entre página e skill agora tem uma casa
  só, e a outra ponta aponta.

### Corrigido

- A regra 12 mandava conferir os nomes de branch no "perfil do
  repositório"; o gancho executa `.claude/branches-protegidas.txt`.
  Agora a regra aponta o arquivo que decide.
- O canivete dizia "listou as sete" com oito skills — o número saiu da
  prosa, que é onde número envelhece.
- `zero-que-mente.md` nomeia a trava (`--no-ignore`) que a tabela medida
  pressupunha e nunca dizia.

## 0.63 — 2026-08-09

Auditoria completa da camada, por instrumento. O que mudou é o que a fase
de prompts mandou; os cortes achados ficaram como proposta.

### Adicionado

- **A auditoria da sessão**, em
  [abrir e fechar a sessão](fluxos/abrir-e-fechar-a-sessao.md): quatro
  perguntas que medem a **camada**, não a sessão — resposta sem o endereço
  da página que deveria ter avisado não entra. E a partida agora manda
  anotar, durante o trabalho, cada adivinhação que a camada deveria ter
  poupado: é o insumo da auditoria, colhido de graça.
- **O pedido pronto de arrumação**, no
  [mapa do repositório](conhecimento/mapa-do-repositorio.md), colado nas
  duas travas que ele obedece: propõe de → para → a regra que manda, nada
  se apaga, e sem a citação da regra não é achado.

### Corrigido

- **A `esfriamento` parou de chamar o cético duas vezes** — a análise de
  promoção já o roda; seis passos viraram cinco. O fecho ganhou escopo
  (o perfil na wiki se atualiza; camada, regras e automação só se
  propõem), o passo do perfil cita a skill `wiki-de-projetos` — é ela que
  preserva a seção declarada pelo dono — e "passo sem matéria não se
  inventa" agora vale para todos os passos. A descrição encolheu um
  terço, e descrição é paga em toda largada.
- **Os dois moldes-exemplo do módulo observabilidade deixaram de ser
  órfãos.** Medido: nada os citava — nem o índice do próprio molde. Agora
  o LEIAME os aponta, e o encerramento diz de qual arquivo cada página
  nasce e onde moram os cinco campos da consulta.

## 0.62 — 2026-08-08

A camada passa a **entregar** a lista de regras, em vez de confiar que ela
será buscada. Zero linha nova no guia.

### Corrigido

- **Regra nova nunca chegava a quem já tinha a camada.** O `--atualizar`
  reescreve as páginas do guia e nunca o `AGENTS.md` — de propósito, porque a
  primeira regra de um repositório público é o oposto da de um privado. Só que
  as regras nascem no modelo de `AGENTS.md`. Consequência medida num
  repositório real com a camada instalada há meses: a lista numerada chegava
  atualizada ao disco a cada atualização, e as regras 11 e 12 **não existiam**
  na sessão dele. A regra estava a doze linhas de distância e nada mandava
  lê-la.

  Agora o `--atualizar` **acrescenta** ao fim do `AGENTS.md` três linhas com o
  endereço da lista — e só se ele não o tiver. Nunca reescreve, nunca
  reordena. Medido: um `AGENTS.md` de 67 linhas próprias sobreviveu com a
  mesma impressão digital, ganhou 6 linhas, e quatro atualizações seguidas não
  acrescentaram nada duas vezes.

  A promessa muda de *"o `AGENTS.md` nunca é tocado"* para *"nunca é
  reescrito"*. O que se acrescenta é o **endereço**, jamais as regras: a lista
  tem uma casa só, e uma cópia dela envelheceria torta justamente do lado que
  a atualização não reescreve.

- **Os três canais de entrega**, novos em
  [mapa do repositório](conhecimento/mapa-do-repositorio.md). Página do guia
  chega a todos e não é lida; `AGENTS.md` é lido sempre e não chega; gancho
  chega e é lido, onde a ferramenta tiver gancho. **Nenhum canal tem as duas
  propriedades** — e não saber disso é o que fazia regra nova morrer no disco.

- **A camada duplicava a própria regra 2**, palavra por palavra, em
  `comece-aqui.md` e em `regras-da-camada.md`. Editar uma faria as duas
  divergirem. A página de entrada agora mostra o **estrago de ignorar** as três
  primeiras regras, e aponta a lista em vez de copiá-la.

## 0.61 — 2026-08-08

Quatro fatos que a consolidação da 0.59 deixou sem casa voltaram — no lugar
onde se precisa deles, não no prompt onde estavam. O guia sobe de 1416 para
1453 linhas e continua 19% menor que antes da consolidação.

### Adicionado

- **Como saber o que o agente de fato carregou**, em
  [mapa do repositório](conhecimento/mapa-do-repositorio.md). A página já
  avisava que abrir a sessão na pasta errada mata as skills **em silêncio**;
  faltava o instrumento. O diagnóstico é em duas partes, e a ordem é o que faz
  a medição valer: com leitura liberada, o agente abre o disco e responde
  certo sobre o que nunca carregou — o falso positivo que faz a camada parecer
  instalada quando não está.

- **As duas travas de quando o agente for arrumar**, na mesma página. *Sem a
  citação da regra, não é achado* — sem ela o agente arruma por gosto, e
  arrumação por gosto é a que se desfaz na semana seguinte. E *nada se apaga*:
  sessão que "limpa" duplicata escolhe sozinha qual das duas versões era a
  verdadeira, e escolhe errado na hora que importa.

- **Três travas para quando o cético ataca o trabalho de outra sessão**, na
  skill `cetico`: rode os instrumentos você mesmo (saída colada é citação, não
  prova), não conserte nada (conferente que arruma devolve mais mudança não
  revisada), e diga o que você contou quando a afirmação for um número — duas
  medições honestas de coisas ligeiramente diferentes discordam, e a
  discordância parece erro quando é definição.

Dois outros fatos ficaram de fora de propósito: *ache a causa raiz antes* e
*não amplie o escopo* já têm comando de fábrica (`/debug` e `/simplify`), e
reescrevê-los em texto era exatamente o que a 0.59 tirou.

## 0.60 — 2026-08-08

### Corrigido

- **O molde do módulo perdeu a coluna `Dono`.** O teste do colega a pegou: o
  portão desta camada lista *quem é dono de quê* como processo de uma empresa,
  não técnica de agente — e o molde viaja para quem instalar o módulo. Uma
  varredura por nome não acharia isso; jeito de trabalhar não tem padrão.

## 0.59 — 2026-08-08

O guia encolheu 21%: de 1792 para 1416 linhas. Nenhum fato se perdeu de
lugar — o que sumiu foi repetição e modelo de prompt para o que já tem
comando.

### Mudou

- **A partida virou um prompt só, e completo.** Ele mora em
  [abrir e fechar a sessão](fluxos/abrir-e-fechar-a-sessao.md) e dá à sessão
  o que ela precisa para **não sair varrendo código**: onde a memória da casa
  mora, o que é pronto, o que ela não decide sozinha. Custa 1278 caracteres —
  entre 0,16% e 0,21% de uma janela de 200 mil. Ele **não repete as regras**:
  elas já chegam pelo `AGENTS.md`, e recopiá-las gastaria a janela duas vezes
  e criaria uma segunda versão para envelhecer torto.

- **`conhecimento/skills-da-camada.md` virou o canivete**: as skills da
  camada, os comandos que vêm de fábrica e os plugins que se pagam, numa
  página só. Ele subiu para o terceiro lugar do menu — a página existia e não
  era encontrada, e isso é problema de endereço, não de conteúdo.

- **`conhecimento/plugins-oficiais-do-claude-code.md` encolheu de 110 para 51
  linhas** e ficou com o que só ele tem: o critério para ler o catálogo
  (`author.name`), o caso do `superpowers` e o comando que conta quantos são
  hoje. A curadoria mudou de casa para o canivete — o mesmo fato em duas
  páginas envelhece torto e passa a mentir de um dos lados.

### Saiu

- **Os modelos de prompt por situação** — refatorar, revisar, corrigir bug,
  entender código, fechar e entregar, auditar, conferir outra sessão. Eles
  descreviam em texto o que `/simplify`, `/code-review`, `/debug` e os outros
  já fazem de fábrica. `fluxos/templates.md` continua existindo como placa,
  apontando para onde as coisas foram: página tirada da origem não some do
  disco de quem já tem a camada, e lá ela ficaria com o texto velho, mentindo.

- Três pedaços eram **conhecimento vestido de prompt** e mudaram de casa em
  vez de morrer: a peneira das cinco perguntas foi para
  [skills: criar e testar](conhecimento/skills-criar-e-testar.md); as duas
  chaves que ligam um plugin, para o canivete; e a espinha da mensagem de
  escalação, para
  [investigação de incidente](fluxos/investigacao-de-incidente.md) — que é
  onde escalação acontece de verdade.

## 0.58 — 2026-08-08

Nasce o primeiro módulo opcional: um copiloto de observabilidade que não se
conecta a ferramenta nenhuma.

```bash
python montar.py --modulo observabilidade
```

### Adicionado

- **O módulo `observabilidade`.** Ele ensina a investigar, cataloga as
  aplicações da casa e compõe as consultas — e fica mais especializado na
  arquitetura de quem o usa a cada incidente. Primeira ferramenta hospedada:
  Datadog, como seção dentro do módulo. Uma segunda entra ao lado sem
  renomear nada.

- **Ele não consulta a ferramenta, e isso é desenho.** Não é falta de
  permissão: licença custa por assento, e agente consultando em rajada deixa
  a ferramenta lenta para a casa inteira. O agente compõe a consulta e diz o
  que esperar; quem roda é o dono. Consulta sugerida e nunca executada é
  hipótese — não vira medido até alguém colar a saída de volta.

- **O log se descarta; o conhecimento se guarda.** Log é grande, envelhece no
  mesmo dia e empurra para fora o que ainda vale. A skill destila seis itens e
  joga o resto fora — inclusive **o caminho que não deu em nada**, que é o
  item que ninguém registra e o que mais economiza tempo na segunda vez.

- **A memória é molde vazio.** A camada entrega a forma; o conteúdo nasce na
  máquina de quem usa e a atualização nunca o sobrescreve. Tudo em tabela e
  lista, contra o estilo do resto do guia de propósito: as páginas do guia são
  para gente ler, a memória é para a IA ler e **atualizar** — e parágrafo não
  se corrige, se reescreve inteiro.

### Corrigido

- **Página de primeiro nível fora do menu agora é descoberta** no
  `site/sidebars.js`. Medido: uma página em `conhecimento/` que a lista
  escrita à mão não cita vira rota e não vira item de menu — órfã silenciosa,
  cobrando contexto e não entregando a ninguém. Módulo opcional não pode ter
  linha fixa naquela lista (ela derrubaria a construção de quem não instalou o
  módulo), então a descoberta era a única saída.

## 0.57 — 2026-08-08

A camada deixa de ser tudo-ou-nada: ela passa a saber instalar parte.

### Adicionado

- **Módulo opcional.** Até aqui, tudo o que entrava no repositório da camada
  chegava em toda máquina que rodasse o `montar.py`. Conteúdo que serve a uma
  ferramenta específica não cabia: seria peso morto para quem não a usa.
  Agora existe uma parte opcional, e ela só chega onde for pedida pelo nome:

  ```bash
  python montar.py --modulos          # o que existe, e o que já está aqui
  python montar.py --modulo <nome>    # instala aquele
  python montar.py --atualizar        # atualiza o instalado; não instala o ausente
  ```

  Sem bandeira, **nenhum byte** do módulo chega ao destino — medido em dois
  repositórios recém-montados: 56 arquivos sem a bandeira, 61 com ela, e a
  diferença é exatamente o módulo mais o espelho da skill dele.

- **A fonte do módulo espelha a árvore de destino** (`modulos/<nome>/…`), e por
  isso não há manifesto: o caminho do arquivo é a declaração de onde ele vai
  parar. Duas listas dessincronizam; um caminho não. Como se escreve um módulo
  está no `modulos/LEIAME.md`.

- **"Instalado" se responde pelo disco, não por arquivo de estado.** Arquivo de
  estado é mais uma coisa para dessincronizar, e a pergunta que importa — isto
  já está aqui? — o disco responde sozinho.

- **O que o módulo entrega para dentro de subpasta de `conhecimento/` é escrito
  uma vez e nunca mais.** É molde: o que nasce ali é memória de quem usa, e a
  atualização não a sobrescreve. A fronteira é a mesma que o mapa do
  repositório já declarava — primeiro nível é da camada, subpasta é da casa.

- **Nome de módulo que não existe é recusado antes do primeiro byte.** Recusado
  na hora de instalar, a montagem já teria criado dezenas de arquivos antes de
  dizer que o nome estava errado.

## 0.56 — 2026-08-07

A camada passa a conferir o que o agente recebe na abertura, o fechamento da
sessão vira skill, e publicar ganha uma regra.

### Adicionado

- **A declaração de MCP da outra ferramenta se cria pelo comando dela** — nova
  subseção em [MCP](conhecimento/mcp.md). Medido: a doc oficial do Devin CLI
  manda declarar MCP num arquivo próprio, e o `devin mcp add` rodado numa
  máquina escreveu a seção `mcpServers` dentro do `.devin/config.json` — o
  formato que a doc já dava por substituído. Quem gerasse esse arquivo pela
  doc acertaria a doc e erraria a máquina, em silêncio. É por isso que o
  `--sincronizar` espelha skill e **não** gera declaração de MCP.
- **`mcp list` diz "declarado", não "funciona"**, em
  [MCP](conhecimento/mcp.md). A lista lê a configuração e não sobe servidor
  nenhum: o registro recém-criado aparece ali mesmo quando o comando
  declarado está errado. É o falso positivo mais fácil de acreditar, porque
  chega logo depois de você registrar.

- **Gancho `conferir-mcp.py`**, um `SessionStart` que lê o `.mcp.json` e
  avisa quando um caminho declarado não existe no disco. Servidor MCP que não
  sobe **não dá erro**: some da lista de ferramentas como se nunca tivesse
  sido configurado, e a sessão trabalha sem ele sem saber. Carrega o próprio
  teste (`--testar`): 5 casos que acusa, 6 que cala.
- **Skill `esfriamento`**: o fechamento da sessão em seis passos — cético na
  conclusão, análise de promoção, candidato a automação, o que a próxima
  sessão precisa saber, o atrito visto de dentro e a revisão das regras. Uma
  linha basta para chamá-la, em vez de colar o roteiro inteiro.
- **Página [abrir e fechar a sessão](fluxos/abrir-e-fechar-a-sessao.md)**,
  segunda no menu. Os dois prompts que se repetem todo dia estavam
  enterrados no meio dos templates; agora têm endereço próprio, e a partida
  encolheu de dez linhas para três.
- **Regra 13: publicar exige revisão semântica, não só varredura.** Varredura
  por padrão acha nome e segredo; jeito de trabalhar e procedência não têm
  padrão e passam inteiros. Exemplo e caso de teste entram na revisão.
- **Seção "O que não entra num teste"** em
  [ganchos](conhecimento/ganchos.md): fixture é onde dado sensível se esconde
  melhor, porque ali "é tudo inventado" e ninguém revisa.

### Corrigido

- **Gancho com caminho relativo prendia o shell da sessão.** O comando do
  gancho roda a partir do diretório atual, que anda a cada `cd`; entrado numa
  subpasta, o gancho some — e num `PreToolUse` de shell o erro passa a vetar
  todo comando, inclusive o `cd` de volta. Impasse fechado. Os três ganchos
  passam a ser registrados com `${CLAUDE_PROJECT_DIR}`, e a atualização troca
  a forma antiga em quem já tinha a camada.
- **Duas seções novas em [MCP](conhecimento/mcp.md):** por que um servidor
  some da lista sem avisar, e por que checar arquivo não basta — sonda que
  fala o protocolo é o único teste que separa "o disco tem bytes" de "a
  ferramenta funciona". Mais a regra do caminho que atravessa mudança de raiz.

## 0.46 — 2026-08-06

Branch de longa duração deixa de depender de boa vontade: vira regra e vira
trava. E o que um segundo agente enxergou da camada.

### Adicionado

- **Regra 12: branch de longa duração e configuração de esteira não se
  tocam.** Integração, homologação, produção — quaisquer que sejam os nomes —
  não se apagam, não se renomeiam, não recebem push forçado e não têm a
  história reescrita; e a automação não se altera de passagem. É
  infraestrutura de outras pessoas: desfazer é público e caro. **Na dúvida se
  uma branch é dessas, ela é.** Os nomes ficam no perfil do repositório.
- **Gancho `vetar-branch-protegida.py`**, a regra 12 virando trava. Um
  `PreToolUse` que lê o comando e recusa apagar, renomear e forçar — porque
  padrão de texto erra dos dois lados: `git push origin +x` é forçado e
  `git push origin x` não é. Ele carrega o próprio teste (`--testar`) com as
  duas listas: 16 casos que barra e 13 que deixa passar, incluindo a forma
  escondida depois de `&&` e a bandeira antes do verbo.
  **Limite declarado:** push normal para branch protegida passa — quem decide
  isso é a regra 9 e o perfil. Veto largo demais é desligado na primeira
  semana.
- **`.claude/branches-protegidas.txt`**, a lista que o gancho lê. É da casa:
  nasce uma vez e a atualização nunca a reescreve. Chega tanto na montagem
  quanto pelo `--atualizar`, porque este não escreve `ARQUIVOS` — sem a
  segunda porta, quem já tinha a camada receberia o gancho e ficaria sem a
  lista.
- **O verificador cobra o veto**: que ele esteja ligado, que passe nos 29
  casos, e que o caminho de passagem seja silencioso.
- **A skill `wiki-de-projetos` preserva a seção `## Declarado pelo dono`.** O
  perfil tem duas metades: o destilado do código, que se regenera, e o que só
  uma pessoa sabe — política de branch, o que a sessão pode empurrar, se o
  repositório é somente leitura. Regeneração que apaga o declarado ensina o
  dono a não declarar nada.
- **Template "conferir o trabalho de outra sessão"**: a conferência vale mais
  numa sessão limpa, que não tem apego à conclusão. O prompt manda rodar os
  instrumentos de novo em vez de crer na saída colada, proíbe consertar (senão
  a auditoria vira mais mudança não revisada) e exige, para cada afirmação
  numérica, que o conferente diga **o que contou** — número sem definição não
  se confere, e duas medições honestas de coisas ligeiramente diferentes
  discordam sem que ninguém tenha errado.

### Corrigido

- **O gancho é de cada ferramenta, e o guia dizia que a `qualidade` entra
  "sozinha, no início de toda sessão".** Medido: outro agente listou as sete
  skills e relatou **nenhum gancho** — a configuração do Claude Code não vale
  para ele. Onde não há gancho, a skill de padrão volta a depender do disparo
  por descrição, que é zero em 160. O guia agora diz isso e dá a saída.
- **A declaração de MCP não viaja entre ferramentas.** Medido: workspace com
  três servidores declarados na raiz, outro agente aberto na mesma raiz
  listou zero servidores e zero ferramentas. A página de MCP passa a separar
  o programa (neutro, em `.agents/mcp/`) da declaração (de cada ferramenta), e
  a avisar que **caminho declarado não é validado por ninguém** — arquivo que
  sumiu continua declarado e vira servidor que não sobe sem dizer por quê.
- **A regra 1 era ambígua e foi lida errado.** "Skill e regra não carregam de
  subpasta" fez um leitor entender que o problema era o lugar do arquivo. O
  que decide é **onde você abre a sessão**. Reescrita nos três lugares onde
  aparece, incluindo o modelo de `AGENTS.md`.
- **A regra 11 estava escrita por extenso dentro da skill `trabalho-por-issue`**
  — quarta cópia do mesmo enunciado. Virou ponteiro: nome, número e endereço,
  sem repetir o texto nem o motivo. A regra tem uma casa (a lista numerada) e
  o reforço nos dois `AGENTS.md`, que é o que vale em toda sessão.
- **A regra 9 dizia "push é do dono" e isso era falso na prática.** Há casa em
  que a sessão empurra o dia inteiro até a branch de homologação. A linha
  divisória não é *push*, é **"isso aciona automação?"**: a permissão é de
  cada repositório e se grava no perfil; sem registro, a sessão não empurra
  nada; e o que aciona esteira, implantação ou aviso a outras pessoas é sempre
  do dono. **Sincronizar não é entregar.**
- **Instrução que não rodava no terminal de quem lê.** Três lugares mandavam
  `cd site && npm install && npm run build`; `&&` é erro de sintaxe no Windows
  PowerShell 5.1. Agora é um comando por linha.

## 0.40 — 2026-08-06

O script confere o que criou, e dois prompts novos para arrumar a casa e
medir o que o agente de fato recebeu.

### Adicionado

- **O `montar.py` confere se o git enxerga o que ele escreveu.** Criar o
  arquivo não bastava: uma linha de ignore sem barra inicial esconde em
  qualquer profundidade, e o que a camada criou não chegava ao clone nem à
  sessão na nuvem — em silêncio, com o repositório parecendo montado. A
  conferência nomeia o arquivo e a regra culpada, com arquivo e linha.
  **Avisa e não conserta**, por dois motivos: as regras de ignore são do
  repositório, não da camada; e o git não reinclui arquivo cujo diretório-pai
  está excluído, então a exceção automática mentiria em parte dos casos.
- **Template "auditar a arrumação do repositório"**: manda a sessão ler a
  regra que vale hoje antes de opinar, exige a citação da regra em cada
  achado, protege a camada multi-fornecedor (a fonte é `.agents/skills/`; o
  espelho do Claude não se edita à mão) e proíbe apagar — o que está fora do
  lugar se move com `git mv`, e destino ocupado vira pergunta.
- **Template "pedir um diagnóstico a outro agente"**: o agente responde o que
  carregou **antes** de poder ler o disco, e só depois compara. A distância
  entre as duas respostas é o relatório — com leitura liberada desde o
  começo, ele responde certo sobre o que nunca recebeu.

### Corrigido

- **Instrução que não rodava no terminal de quem lê.** Três lugares mandavam
  `cd site && npm install && npm run build`; `&&` é erro de sintaxe no
  Windows PowerShell 5.1. Agora é um comando por linha.

## 0.39 — 2026-08-06

Revisão do guia inteiro, corte de contexto e a regra que impede a sessão de
improvisar procedimento.

### Adicionado

- **Regra 11: não invente passo onde já existe receita.** Antes de propor como
  se faz algo que a casa já faz — subir uma peça, publicar, liberar acesso —, a
  sessão procura o procedimento na documentação dela e cita a origem de cada
  passo; não achando, pede o endereço em vez de improvisar. Entrou em dois
  lugares: a lista numerada e o modelo de `AGENTS.md` — porque skill dispara em
  metade dos pedidos e linha no `AGENTS.md` vale em toda sessão.
- **A skill `trabalho-por-issue` virou executável**: o bloco que a casa
  preenche uma vez e grava no perfil do repositório, as três recusas na
  abertura, a régua de critério verificável, os quatro tipos de comentário e a
  sequência da sessão com os buracos da casa marcados.

### Corrigido

- **O gancho local não viaja mais dentro do script.** As páginas embutidas
  vinham de um glob `.claude/hooks/*.py`, que varria também o gancho pessoal de
  quem trabalha no repositório da camada — arquivo fora do git, que lê um
  arquivo de uma máquina só. Agora o gancho da camada entra nomeado.
- **Contagens escritas à mão saíram da prosa**: o README dizia "três skills"
  e a página de entrada dizia "seis"; são sete. Número em prosa mente na
  próxima skill — quem conta agora é o índice.
- **`zero-que-mente` anunciava duas causas** e listava cinco.
- **A lista do que vem de fábrica envelheceu**: entraram os comandos novos,
  saíram os que não se confirmam mais, e a página passou a dizer que a lista
  muda entre versões e onde conferir.
- **A coluna do Codex em `subagentes` saiu**: o endereço não foi conferido em
  máquina nenhuma, e afirmação sem instrumento não entra.

### Mudado

- **A camada custa menos em toda sessão**: 7 861 → 6 589 caracteres no
  repositório da camada. O gancho da qualidade parou de injetar o frontmatter
  (nome e descrição já chegam pelo catálogo de skills), e `AGENTS.md` e
  `CLAUDE.md` pararam de repetir a árvore do mapa do repositório.
  A conta é `AGENTS.md` + `CLAUDE.md` + o nome e a descrição de cada skill +
  o que o gancho **de fato imprime** — sem as chaves `name:` e `description:`,
  que a ferramenta rende do jeito dela. Contando de outro jeito o número muda,
  então o número só vale junto com a definição.
- **A página de plugins encolheu à metade**: ficou o critério para ler o
  catálogo, o comando que o confere e os plugins que resolvem dor que se
  repete. Lista de nomes sai — o atlas não é catálogo.
- **História em issue tem uma casa só**: a página do guia ficou com o desenho
  e o porquê; tudo o que se executa mora na skill.

## 0.37 — 2026-08-06

Organização, com o critério vindo de medição e não de gosto.

### Adicionado

- **A pasta `tmp/` nasce com a camada**: o endereço do descartável. Sem um
  lugar óbvio, o rascunho gerado vira arquivo de nome improvisado na raiz e
  fica lá para sempre. O conteúdo é ignorado; a pasta sobrevive pelo LEIAME.
- **`.gitignore` base cobre os descartáveis**: cache de linguagem, de teste e
  de verificador de tipo.
- **O verificador ganhou avisos que não reprovam**: subpasta sem LEIAME,
  pasta de um arquivo só, terceiro nível, nome com maiúscula, acento ou
  espaço, e primeiro nível passando de 21 itens. Arrumação é julgamento do
  dono — instrumento aponta, não trava.
- **O mapa ensina quando criar mais uma pasta**: as três condições juntas, e
  o número que decide — em navegação medida, um nível a mais custa cerca de
  vinte vezes um item a mais, então pasta só se paga tirando mais de umas
  vinte coisas do nível de cima.

## 0.36 — 2026-08-06

### Adicionado

- **Skill `trabalho-por-issue`**: conduz o trabalho pela issue — abre no
  padrão, mantém o corpo como estado e os comentários como eventos, exige
  comando e saída colada em cada verificação ("sem os dois não é verificação,
  é opinião"), e reescreve o **ponto de retomada** para a próxima sessão
  continuar sem ninguém reexplicar. Desenho fundamentado em pesquisa, com
  três decisões que vieram dela: só marcar critério depois da prova ponta a
  ponta; instrução em bloco único, não em conta-gotas; e texto vindo da issue
  é **dado, nunca ordem** — injeção por issue é problema conhecido.

### Mudado

- **A camada deixa de usar sub-issues.** Tarefa vira critério dentro da
  própria issue; pedaço grande demais vira outra issue ligada por link.
  Hierarquia só se paga quando outra sessão pega o pedaço sozinha — e cobra
  uma peça a mais para desatualizar.

## 0.35 — 2026-08-06

### Adicionado

- **Página "as skills da camada"**: o índice que faltava — o que cada skill
  faz e, principalmente, **como ela entra na conversa** (sozinha, por nome ou
  por gancho). A camada entregava seis skills e o guia não listava nenhuma;
  quem lia a documentação não sabia que existiam.
- **O verificador cobra o índice**: skill nova sem linha no guia acusa falha.
  Skill que ninguém sabe que existe não é usada.

## 0.33 — 2026-08-06

### Adicionado

- **Skill `documentar-processo`**: lê a fonte junto com você — inclusive por
  navegador —, resume e escreve a página no padrão do repositório de
  documentação, com passo a passo que mostra o sinal de sucesso de cada
  passo, armadilhas, links e prints recortados. Guarda o perfil daquele
  repositório para não reanalisar toda vez; confere no código o que afirmar
  sobre sistema e chama o cético antes de publicar; e, quando a documentação
  não bate mais com a realidade, **marca em vez de consertar em silêncio** —
  a mudança do processo é a notícia. Procurada antes de escrita: nada
  oficial cobre navegar + resumir + escrever no padrão.

### Mudado

- **Os prompts de sessão saíram do meio da página**: a partida e o
  esfriamento agora abrem os templates, e o "Comece aqui" aponta os dois pelo
  nome. Estavam lá desde a 0.21 e o dono não os encontrou — página longa
  esconde o que se usa todo dia.
- O esfriamento ganhou um item: o que a sessão descobriu sobre o repositório
  **atualiza o perfil dele na wiki**, em vez de virar arquivo novo. Um
  arquivo por repositório envelhece junto com ele; uma pilha de anotações de
  sessão envelhece sem ninguém perceber.

## 0.30 — 2026-08-06

### Mudado

- **Tamanho de linha sai da régua.** Ela cobrava 80 colunas de tudo — e caía
  onde não paga: anotação da casa, perfil gerado, registro de incidente.
  Ninguém requebra aquilo, e aviso que ninguém atende ensina a ignorar aviso.
  As páginas da camada seguem em 80 colunas por hábito de quem escreve. Quem
  quiser a disciplina de volta liga na sua pasta, com um `.markdownlint.jsonc`
  próprio — configuração de pasta vence a da raiz.

## 0.29 — 2026-08-06

Dois falsos negativos, achados rodando o ritual num repositório que **recebeu**
a camada — nenhum dos dois aparecia no repositório de origem.

### Corrigido

- **A sonda de instruções não se aplica em toda casa.** Ela pergunta pelas
  pastas da camada; num repositório com `AGENTS.md` próprio, a resposta certa
  é outra e a checagem acusava falha que não era defeito. Agora ela confere se
  a pergunta cabe naquele `AGENTS.md` e, quando não cabe, pula dizendo por quê.
- **A régua prometia um conserto que não existe.** A regra de alinhamento de
  tabela não tem correção automática: o comando que o guia manda rodar não a
  resolve, e o aviso ficava lá para sempre. A regra saiu da régua — o site
  renderiza igual, e cobrar o que a ferramenta não conserta faz gente ignorar
  aviso de verdade.

## 0.28 — 2026-08-06

### Adicionado

- **Mais duas causas de zero que mente**, vindas de uso e verificadas aqui:
  o filtro que espera um fim que nunca chega (`tail` de processo que não
  termina devolve nada, para sempre — e o nada parece "não subiu"), e a
  interface que não está no arquivo buscado (item dentro de componente
  colapsado não nasce no HTML; a rota existe e a busca diz que não).

## 0.27 — 2026-08-06

### Mudado

- **O site passa a publicar as subpastas de `conhecimento/`** — a wiki que a
  skill gera e as notas da casa deixam de ser invisíveis. Um nível só: o site
  enxerga a raiz, e mais alcance arrastaria os repositórios de código.
- **O menu descobre a casa sozinho**: as páginas da camada seguem escritas à
  mão, na ordem de leitura, e depois entra uma categoria por subpasta,
  encontrada na construção — nome livre, rótulo vindo do título do `LEIAME`.
- **`.md` é lido como markdown comum, não como MDX.** Era a razão de a
  subpasta ficar de fora: um `<coisa/assim>` fora de bloco de código derrubava
  a construção com um erro que não dizia onde consertar. Reproduzido e
  corrigido na raiz — quem precisar de componente escreve `.mdx`.
- O `LEIAME` de subpasta passa a ser página: nela ele costuma ser conteúdo (o
  mapa da wiki), não recado de pasta. No primeiro nível continua fora.

## 0.26 — 2026-08-06

### Adicionado

- **A ordem de atualizar**: repositório com remoto traz o que já foi
  empurrado **antes** de rodar a camada — senão a versão nova cai sobre uma
  árvore velha e o conflito aparece com a camada no meio.
- **Terceira causa de zero que mente**: o terminal que reescreve o argumento.
  No Windows, o Bash do Git converte argumento começando com barra em caminho
  do sistema, sem avisar — e o programa responde honestamente sobre a coisa
  errada. Medido, com o conserto.

## 0.23 — 2026-08-06

Verificação adversarial de conclusão, e o fluxo que leva do sintoma à causa.

### Adicionado

- **Skill `cetico`**: verificação adversarial de uma conclusão — separa
  provado de suposto, desenha a medição que derrubaria cada suposição, e
  reemite o veredito em provado / provável / não provado.
- **Fluxo de investigação de incidente**: do sintoma à conclusão, em nove
  passos, sem depender de ferramenta. Fecha com o raciocínio que resolve —
  artefato imutável igual + hora exata de mudança = a configuração é a
  variável.
- **Página "zero que mente"**: por que uma busca devolve vazio e o vazio
  engana. Duas causas medidas: o filtro que você não sabia que estava ligado
  (busca respeita o `.gitignore` e some com pastas inteiras, sem avisar) e o
  vocabulário errado (o nome que o código escreve não é o que fica gravado).
- **Template de escalação para outro time**: escopo medido e não amostrado,
  identificadores que o receptor consegue procurar, e o pedido acionável —
  evidência sem pedido é escalação pela metade.

### Mudado

- O esfriamento da sessão passa a pedir o cético antes da promoção, e a
  apontar o atrito do dia: o que atrapalhou e o que o dono poderia ter feito
  diferente.
- A skill de promoção exige conclusão auditada antes de promover: lição
  errada promovida sai de uma casa e entra em todas.
- A página de MCP ganhou o gatilho de "quando vale escrever o seu": ritual
  repetido, parâmetro que causa erro silencioso vira obrigatório.
- O mapa corrige uma meia-verdade: `.gitignore` esconde do git **e da
  busca** — só a leitura direta continua funcionando.

## 0.21 — 2026-08-05

### Adicionado

- **As regras da camada**, numeradas de 1 a 10, com o rito de propor
  mudança citando o número.
- **Dois templates de sessão**: a partida (regras, estrutura e como não
  varrer repositório grande inteiro) e o esfriamento (promoção do genérico,
  candidatos a automação, crítica às regras).
- **Análise de promoção** como skill e como regra: ao dar por pronto, três
  pilhas — genérico, da casa, descartável.
- Skills novas de conhecimento do conjunto: **wiki de projetos** (agora
  incremental: consulta o índice, tipa o repositório, poucos por rodada) e
  **antes de criar** (procurar e citar antes de implementar).

### Mudado

- O script ficou enxuto: a versão é a primeira linha dele; a instrução mora
  no guia.
- Regra econômica para os agentes: repositório grande não se varre inteiro;
  rede e MCP só quando a tarefa exigir, com pausa entre chamadas.
- A varredura de markdown respeita as fronteiras do que não é da camada.

## 0.9 — 2026-08-05

### Mudado

- A skill `wiki-de-projetos` deixa os perfis **na régua sozinha**: roda o
  conserto do markdownlint ao terminar de gerar.
- O mapa ensina o conserto manual (`npx markdownlint-cli2 --fix ...`) e a
  régua entrou na árvore do repositório.

## 0.7 — 2026-08-05

### Corrigido

- **A estrutura do workspace agora viaja no git.** As pastas do esqueleto
  eram ignoradas inteiras e não chegavam num clone; agora só o conteúdo fica
  de fora — o LEIAME segura cada pasta, e o publicador de tokens viaja na
  `.credenciais/`. Segredo e projeto pessoal continuam sem entrar em git
  nenhum (provado com clone real).

## 0.6 — 2026-08-05

### Mudado

- O atlas entrega **um script só**: o `montar.py`. A verificação de agentes
  virou ferramenta local do autor — nem toda máquina tem todos os agentes
  instalados para medir, e a falta dela não pode sujar quem recebe a camada.

## 0.5 — 2026-08-05

### Adicionado

- **Régua de markdown** (`.markdownlint.jsonc`) nasce com a camada — o editor
  e o verificador leem a mesma; o verificador acusa markdown fora dela e diz
  o comando que conserta.

### Corrigido

- Todos os markdowns da camada entram na régua: tabelas realinhadas, linhas
  requebradas em 80 colunas — os avisos do editor somem.

## 0.4 — 2026-08-05

### Adicionado

- O modelo de `AGENTS.md` nasce com as regras da casa completas: abrir na
  raiz, credencial não se abre, destrutivo é do dono, pronto só com prova de
  instrumento.
- O esqueleto traz o **publicador de tokens**: valores em
  `.credenciais/mcp.env`, `publicar-mcp-env.py` os publica como variáveis —
  e o `.mcp.json` fica só com `${NOME}`, nunca com segredo.

## 0.3 — 2026-08-05

### Adicionado

- Página **Comece aqui** abrindo o guia: o que a camada instala, como usar,
  as três regras que não mudam.
- **CHANGELOG** (este arquivo) e `--versao` nos comandos.

### Mudado

- README reescrito: cada passo diz o que aparece quando dá certo.
- Menu do guia na ordem da jornada: comece aqui → mapa → templates → o resto.
- O mapa ganhou os casos de borda da atualização ("editei uma página da
  camada", "apaguei uma página").

## 0.2 — 2026-08-05

### Adicionado

- **O site do guia viaja com a camada**: montar em qualquer máquina traz o
  `site/` pronto para `npm install && npm run build`.
- **Versão da camada**: sobe sozinha quando o conteúdo muda; todo comando a
  imprime.
- O contrato da atualização no mapa: o que a camada sobrescreve, o que é seu.
- O modelo de `AGENTS.md` nasce com a regra "procure antes de criar" — skill
  sozinha dispara em só metade dos pedidos (medido).

## 0.1 — 2026-08-05

Linha de base do dia:

- O montador passou a levar **tudo**: páginas, skills, ganchos — antes as
  skills ficavam para trás em silêncio.
- Esqueleto do workspace virou opção (`--esqueleto`), com `.gitignore`
  ancorado na raiz.
- Padrão de qualidade entra sozinho por **gancho** em toda sessão (medido:
  três em três; sem gancho, zero).
- Espelho de skills entra no git — sessão na nuvem passa a ter skills.
- Ponte do Devin desligada: skill uma vez só, negações de credencial próprias.
- Skills novas: **wiki de projetos** e **antes de criar**.
- Verificador ganhou `--camada`, a prova do gancho e a caça a arquivo órfão.
