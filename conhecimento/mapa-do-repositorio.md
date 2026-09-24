# Onde escrever cada coisa

Antes de criar arquivo, ache a pasta certa aqui. O erro que esta página
evita é o mais caro do repositório: escrever no lugar errado, o texto não
chegar em quem precisava, e ninguém perceber.

A regra que resolve quase tudo: **quem vai ler decide onde mora.** Se quem
lê é gente, é página. Se quem lê é instrumento, é dado. Se só serve à sua
máquina, fica fora do git.

## As pastas, uma linha cada

| Pasta | O que mora ali | Viaja para quem instala? |
| --- | --- | --- |
| `conhecimento/` | página que gente lê | só as que a tupla `FONTES` do `montar.py` nomeia: `regras-da-camada.md` — a lista das regras gerada de `nucleo/regras.json` —, as duas receitas de quem instala, `verificacao-pos-atualizacao.md` e `organizar-conhecimento-e-projetos.md`, `motores-auxiliares.md` e [`windows-e-git-bash.md`](windows-e-git-bash.md), as armadilhas do Windows com Git Bash e o conserto de cada uma. As outras páginas ficam neste repositório: quem instala recebe regras, skills, instrumentos e ganchos, e a documentação da camada mora aqui |
| `conhecimento/projetos/` | a wiki dos repositórios vizinhos — um perfil por repositório, gerado pela skill `perfil-de-repositorio` | não: é conteúdo do workspace, fora do git |
| `.agents/` | instrumentos (Python), as skills (fonte) e dois prompts: `.agents/prompts/bootstart.md`, o briefing de abertura para qualquer agente — o que a sessão vai encontrar, o que os ganchos recusam, e que skill ou receita atende cada pedido — e [`.agents/prompts/partida.md`](../.agents/prompts/partida.md), o checklist de partida, que roda sob demanda, em qualquer agente, e devolve o relatório GO ou NO-GO | os instrumentos, as skills e os dois prompts, sim. Quem tem comando de barra chega neles por `/bootstart` e `/partida`; quem só carrega o arquivo de instruções da raiz chega pelo `AGENTS.md`, que manda ler o briefing e aponta a partida para quando o dono pedir; e o primeiro comando do briefing é a saúde da abertura |
| `.claude/` | o que o Claude Code lê: ganchos, subagentes, cópia das skills e a regra por caminho do padrão de código, gerada da skill | sim |
| `nucleo/` | os dados que instrumento lê (JSON) | sim |
| `modulos/` | peça opcional, que só chega para quem pedir pelo nome | não |
| `execucoes/` | roteiros do executor, **cópia gerada** de `modulos/encadeador/execucoes/` — edite lá, nunca aqui; o resultado de cada rodada fica fora do git | só com `--modulo encadeador`: os roteiros nomeados chegam pelo módulo, não pela camada base |
| `tmp/` | rascunho, fora do git. Trabalho em curso também mora ali — evidência de execução, entrada de migração —, então olhe antes de apagar: o `LEIAME.md` da pasta diz o que é insumo vivo | não |
| `projetos/` | os repositórios de código clonados, um por pasta, cada um com o seu próprio git; só o `LEIAME.md` é rastreado aqui | só com `--esqueleto`: o instalador cria a pasta com o `LEIAME.md`, e o conteúdo é do workspace |
| `recursos/` | material de terceiro — template comprado, kit de design, manual, base de referência — com licença própria e fora do git; só o `LEIAME.md` é rastreado | só com `--esqueleto`: o instalador cria a pasta com o `LEIAME.md` |
| `.credenciais/` | senhas, chaves e tokens, fora de todo git; rastreados só o `LEIAME.txt` e o `publicar-mcp-env.py`, que publica os nomes do `mcp.env` no ambiente | só com `--esqueleto`: o instalador entrega o `LEIAME.txt` e o publicador |
| `.devin/` | o que o agente de terminal lê: o `config.json` com o muro de leitura sobre credencial e a pasta de skills | não: chega pela ponte `--devin`, que ajusta o `config.json` de quem instala em vez de copiar esta pasta |

Na raiz ficam as instruções (`AGENTS.md`, `CLAUDE.md`, `README.md`) e os
instrumentos que agem sobre o repositório inteiro. Nenhum viaja: o
`montar.py` instala a camada rodando do clone dela, de dentro do repositório
que a recebe, e lê só o que o git rastreia aqui. Os outros três também ficam
neste repositório e **não chegam a quem instala**: `publicar.py` leva o que é público para fora,
`verificacoes.py` é a porta única das verificações e `verificar-agentes.py`
é a mais larga delas.

Nem toda verificação protege quem instala. A rotina `camada` — a mais larga
— roda o `verificar-agentes.py`, que **não viaja**: consertar algo nela
protege este repositório e mais ninguém. Quem instalou a camada é protegido
pelo `.agents/camada/camada.py`, que viaja junto. O alcance de cada rotina
está declarado no catálogo do `verificacoes.py`, campo `alcance`: **fica no
atlas** ou **viaja com a camada**. No atlas, `python verificacoes.py --listar`
mostra a coluna; onde a camada foi instalada esse arquivo não existe, e o que
se tem é `python .agents/camada/camada.py medir provar`.

## Página ou dado?

Esta é a decisão que mais erra, e a regra 14 é quem manda.

- **Dado** é o que instrumento consome: um fato por chave, sem prosa em
  volta. Mora em `nucleo/*.json`. Exemplo: as regras da camada nascem em
  `nucleo/regras.json`.
- **Página** é o que uma pessoa lê para entender. Mora em `conhecimento/`.

Quando o mesmo fato interessa aos dois, ele nasce como dado e a página é
**gerada** a partir dele — nunca escrita à mão em dois lugares. É o que
acontece com `conhecimento/regras-da-camada.md`: editar essa página é
trabalho perdido, porque a próxima sincronização a reescreve.

Depois de mexer em página, skill, módulo ou `nucleo/`, rode:

```bash
python montar.py --sincronizar
```

## Fonte e cópia: edite sempre a fonte

Três pares neste repositório parecem duplicados e não são. Em cada um há uma
fonte e uma cópia gerada; editar a cópia é trabalho que a próxima
sincronização apaga.

| Fonte (edite aqui) | Cópia (gerada) |
| --- | --- |
| `.agents/skills/` | `.claude/skills/` |
| `modulos/<nome>/` | os arquivos correspondentes na raiz |
| `nucleo/regras.json` | `conhecimento/regras-da-camada.md` e o `AGENTS.md` |

A cópia das skills **entra no git de propósito**: sessão que roda na nuvem
só enxerga o que está commitado. Vale igual para a página de cada módulo
instalado, [o índice](indice.md) e [a voz](voz.md), que nasce em
`modulos/<nome>/conhecimento/` e é reescrita pela sincronização: deixá-la
fora do índice a esconde do clone e da sessão na nuvem, e o instalador avisa
isso a cada atualização.

O `montar.py` não carrega cópia nenhuma: ele lê a camada da pasta em que
mora, só o que o git rastreia, e grava no destino o registro do que instalou,
em `.agents/camada/registro-da-instalacao.json`. Editar uma fonte não
regenera o instalador. A história antiga dele, quando carregava o depósito,
continua no `.git`: `git count-objects -vH` separa o objeto solto (`size`) do
empacotado (`size-pack`).

A metade que falta: **skill pessoal não entra aqui.** Skill que só serve a
você vai para as skills de usuário, em `~/.claude/skills/` — fora do
repositório, fora do git. Skill que entra em `.agents/skills/` é skill que
todo mundo que instalar a camada recebe, e passa a cobrar contexto de toda
sessão de todo mundo.

## Gancho novo se matricula em cinco pontos

Arquivo que precisa chegar em quem instala se matricula no `montar.py`, e se
commita: o instalador só leva o que o git rastreia. O `--verificar` checa os
arquivos que conhece e cala sobre o que ninguém matriculou: gancho commitado e ligado atravessa o "tudo em dia" sem
viajar.

Página nova em `conhecimento/` NÃO viaja sozinha: a tupla `FONTES` nomeia
página por página, e a que não estiver lá fica neste repositório. Skill nova
entra sozinha, porque `FONTES` carrega `.agents/skills/` inteira. Gancho
novo, não. São **cinco pontos**, todos no
`montar.py`:

1. A constante com o caminho do arquivo.
2. A constante com o comando que entra no `settings.json`.
3. O `GanchoDeclarado`, que amarra evento, matcher e comando.
4. A tupla `FONTES`, que diz o que viaja.
5. A sequência `garantir_ajustes`, que instala.

**Cerca de `PreToolUse` troca o quinto ponto pelo sexto.** Quem tem linha
própria no `settings.json` é só o **despachante das cercas**
(`.claude/hooks/despachar-cercas.py`), com o matcher que é a união de todas;
cada cerca entra na tupla `CERCAS` dentro dele, com o matcher dela, e **não**
entra no `garantir_ajustes`. Então o matcher de uma cerca é escrito em dois
lugares — o `GanchoDeclarado` e a lista do despachante — e isso é de
propósito: um é o contrato, o outro é a implementação, e a rotina `matricula`
compara os dois e acusa quem divergir. O `GanchoDeclarado` de uma cerca
parece morto para quem varre por AST, porque quem o lê o acha por reflexão
sobre o espaço de nomes do instalador, não pelo nome.

O gabarito é o commit que estreia um gancho: os pontos aparecem juntos
no mesmo diff. E a prova não é reler o instalador: é montar árvore virgem,
rodar de dentro dela o `montar.py` deste repositório, e ver o arquivo chegar.

**Gancho que vigia a sessão se edita fora da árvore dela.** Os ganchos rodam
da árvore em que a sessão abriu; editar um ali e errar tranca a própria
sessão. Quando o agente não pode escrever em outra worktree, despache um
subagente com worktree própria: caso vermelho antes, o `--testar` provado lá,
e o commit trazido por mescla, com o `--testar` rodado de novo aqui.

**O despachante é um processo para todas as cercas, e o preço é o
isolamento.** Com uma linha no `settings.json` e um processo por cerca, uma
chamada de `Bash` paga a partida de todos eles; com o despachante, paga uma
só. Em troca, as cercas deixam de ser independentes: se o despachante não
sobe, **todas** caem juntas. Ele paga isso negando por conta da cerca que
estourar, em vez de deixar passar sem cerca, e continua avaliando as outras.

Toda linha de gancho chama o Python pelo nome que o instalador mediu nesta
máquina, e o próprio Python acha o gancho: `python -X utf8 -c "..."
.claude/hooks/<arquivo>.py`. O `-X utf8` liga o modo UTF-8 do Python só para
o gancho: a entrada e a saída saem em UTF-8 também na máquina que não o liga,
e sem ele um caractere fora do cp1252 derruba o gancho, que então deixa a
ferramenta passar. O programa curto do `-c` lê a raiz em
`CLAUDE_PROJECT_DIR`, ou no diretório atual quando a variável falta, põe a
pasta dos ganchos no lugar do diretório atual no caminho de importação, e roda
o gancho no mesmo processo; gancho que falta sai 2, que barra. **A linha não
tem variável no texto de propósito.** O Claude Code roda o gancho pelo Git Bash
no Windows; o Copilot, com a pasta confiada, roda o mesmo `.claude/settings.json`
por uma concha que não expande `${...}`, e já entrega a variável no ambiente e
a entrada no formato do Claude; a ponte do Codex e do Devin roda as cercas pelo
cmd. Só uma linha sem variável no texto roda igual nas três; a prova é a
sonda recusada no Copilot pela cerca do próprio Claude.

O **lançador**, `.claude/hooks/interpretador.sh`, fica para a linha de reserva,
quando nenhum Python respondeu na instalação, e para as pontes do Codex e do
Devin. É um script de bash que escolhe o interpretador por execução — o primeiro da
lista dele que responde `3` a `-c "import sys; print(sys.version_info[0])"` —
e entrega o gancho a ele. Ele existe porque o nome `python3` não é universal:
no Windows é o atalho da loja, que está no PATH, não roda, e `which` dá por
presente. A lista de candidatos mora só nele; a rotina `camada` e o gancho
`verificar-ambiente` a leem de lá e julgam cada nome executando, nunca por
`which`. **A ordem dos candidatos sai da plataforma, não de uma lista só:**
em Windows o lançador tenta `python py python3`, e no resto `python3 python
py` — porque tentar o atalho da loja primeiro faz cada gancho pagar a sonda
de um nome que não roda.

**E ele lembra quem respondeu, senão sonda de novo a cada chamada.** O nome
escolhido fica num arquivo da pasta privada do usuário — `XDG_RUNTIME_DIR`
onde existe, `LOCALAPPDATA` no Windows; sem nenhuma das duas não há lembrança
e ele só sonda —, estado que não viaja, e a chamada seguinte o usa direto.
A lembrança não é confiada às cegas, porque conteúdo de arquivo é dado, nunca
ordem: só vale se for arquivo regular, do próprio usuário e não um link; só
vale se o nome estiver na lista de candidatos do próprio lançador, nunca um
caminho; e a escrita é atômica, por arquivo próprio movido por cima. Fora
disso o lançador sonda outra vez e reescreve. O `--testar` dele planta um
impostor na lembrança e prova que o Python roda no lugar dele. Com a
lembrança, o piso de cada chamada é o bash mais a partida do Python; chamar
o Python direto tira também o bash, e por isso a linha chama o Python pelo
nome medido na instalação, e o lançador fica como reserva.

**Quando nenhum nome responde, o lançador sai 2, que é a única saída que
barra.** A documentação oficial dos ganchos é explícita: em `PreToolUse` só
o código 2 impede a chamada, e qualquer outro código diferente de zero é
erro que **não** barra. O lançador saía 1 — então, numa máquina sem Python,
as cercas falhavam abertas e só um aviso no erro do gancho denunciava. Cerca
que não roda não deixa passar. Ele também diz isso no erro do gancho
em vez de morrer calado. Ele viaja em `FONTES`, sem evento nem matcher, e o
instalador reescreve no lugar a linha de gancho que ainda nomeia um
interpretador.

**Cerca que roda mas não lê a lista de que depende também não libera.**
Lista vazia e lista não lida são estados diferentes. Tratar a falha de
leitura como lista vazia significa "nada é protegido", e a cerca libera
calada, com código zero, exatamente quando ficou cega. Quem lê a lista
devolve os dois fatos, os nomes e se mediu, e a cerca recusa dizendo que não
mediu. A recusa é cirúrgica: só o alvo cujo repositório é OUTRO, medido pelo
caminho e não pelo nome da pasta. Escrita dentro da própria árvore continua
livre, senão clone novo, worktree nova e sessão na nuvem, que legitimamente
não têm a lista, ficariam trancados.

**Gancho se edita em sessão do dono, não dentro de uma execução.** O
`vetar-escrita-em-politica` recusa escrita em `.claude/hooks/`, no
`settings.json`, nas listas que as cercas leem e em `nucleo/regras.json`
enquanto a marca `ENCADEADOR_ETAPA` estiver no ambiente. Em sessão
interativa a marca não existe e a cerca não morde: é essa a saída do laço
— o gancho que protege os ganchos protege a si mesmo, e quem o muda é
quem não está sendo vetado por ele.

**A sessão que só pesquisa não escreve no repositório.** Mesma técnica,
outra marca: com `ATLAS_SO_LEITURA` no ambiente, o
`vetar-escrita-em-sessao-de-pesquisa` recusa escrita em qualquer caminho
de dentro da raiz — inclusive `tmp/` e arquivo temporário —, e o
`cobrar-destino-da-entrega` **cala**, porque não há destino em disco a
cobrar. Rascunho e medição vão para a pasta temporária da máquina, que o
sistema limpa sozinho; o que a sessão apurou vai para a issue. Quem abre
sessão assim segue a seção "A sessão que só pesquisa" do
[bootstart](../.agents/prompts/bootstart.md), que declara o trato inteiro. Sem a marca nada disso acontece: a sessão é
uma sessão comum.

**Aviso que só informa sai uma vez por sessão; o que pede ação sai sempre.**
Gancho de parada roda a cada turno, e aviso repetido vira ruído que a sessão
e o dono aprendem a ignorar. O que pede ação da sessão, como commit que não
saiu da máquina, se repete enquanto estiver pendente. O que é só para saber
grava uma marca por sessão na pasta temporária e volta só quando o texto
muda. Sem identificador de sessão, fala sempre: sem onde lembrar, calar
seria perder o aviso.

**A saída do gancho vai em JSON com `ensure_ascii=True`.** Sem o modo UTF-8
do Python, o stdout de um processo filho no Windows é cp1252, e um caractere
fora dele, como um nome de arquivo com emoji, estoura o `print`. O gancho
sai com erro e cala, e o que ele ia dizer se perde. JSON em ASCII chega ao
leitor com o mesmo texto.

## Instrumento novo se matricula em um ponto

Instrumento de `.agents/` é mais barato que gancho: ele não tem evento nem
matcher, então basta **a tupla `FONTES`** do `montar.py` — o mesmo quinto
ponto do gancho, sozinho. Quem seguir a receita das cinco linhas para um
instrumento procura quatro pontos que não existem.

Duas saídas dessa matrícula, e as duas são declaração:

- **Instrumento que só serve a este repositório não viaja.** Ele se declara em
  `INSTRUMENTOS_QUE_FICAM`, no `.agents/camada/camada.py`, com o motivo
  escrito ao lado. É o caso do `.agents/saude/saude.py`, que mede este
  repositório contra o instalador dele.
- **Instrumento que chega por módulo já viaja pelo módulo**: o leitor do
  instalador o leva de `modulos/<nome>/`. Repetir a linha no `FONTES` faria o
  mesmo arquivo entrar duas vezes.

A rotina `matricula` cobra o saldo dos dois lados: rastreado fora do `FONTES`
(não viaja, e quem instala não recebe) e declaração que sobra (a exceção
sobreviveu ao arquivo). Rode-a sempre que entrar ou sair instrumento — e
repare em QUAL comando, porque o `verificacoes.py` **não viaja**:

```bash
python verificacoes.py matricula              # aqui, no atlas
python .agents/camada/camada.py --matricula    # em quem instalou a camada
```

## Função repetida entre ganchos muda em todos

Cada gancho é um arquivo que roda sozinho, sem biblioteca comum — de
propósito. O preço é que a mesma função está copiada em vários ganchos —
conte com `grep -h '^def ' .claude/hooks/*.py | sort | uniq -c | sort -rn`,
porque número escrito aqui envelhece calado.

Consertar uma dessas em um gancho só reprova a rotina `camada`: ela compara
as **cópias** de mesmo nome entre ganchos e acusa quando duas divergem. Ou
muda em todos, ou declara a divergência em `FUNCOES_QUE_PODEM_DIVERGIR`, com
o motivo escrito ao lado.

## Página nova precisa de quem a leia

Uma página que nenhuma outra cita é órfã: ela cobra contexto de toda sessão
e não entrega a nenhuma. Por isso a verificação da camada reprova página sem
link de entrada. Ao criar uma, cite-a de algum texto que já é lido — e, se
não houver de onde citar, provavelmente ela não devia existir.

## Achado que não vira arquivo vai para a caixa

Nem tudo que a sessão descobre vira página. Defeito e ideia de melhoria viram
linha nas issues permanentes, escritas pelo `.agents/caixa/caixa.py` — e não
trabalho fora do assunto de agora. Cada linha leva a etiqueta do seu tipo, e
por isso as duas caixas podem apontar para a MESMA issue: um quadro só. Linha
que acabou sai por `caixa.py podar --id <identidade>`, que tira a linha do
quadro e deixa o registro do fechamento em comentário da caixa.

O relatório de fim de rodada não é linha: `caixa.py relatar --corpo <texto>`
abre um comentário NOVO na mesma caixa, um por rodada. Linha se reescreve por
desenho, e por isso o quadro só guardaria a última — o comentário guarda todas.

Para **ler** essas issues use `gh api ... -q .body`, nunca `gh issue view`. O
`view` renderiza o markdown e come as marcas HTML que delimitam o bloco do
instrumento. Quem reescreve o corpo a partir do que o `view` mostrou apaga as
marcas, e a próxima escrita do `caixa.py` se perde.

## O que a camada garante em cada ferramenta

Medido rodando outra ferramenta de agente sobre esta árvore: a camada tem
duas metades, e as duas atravessam — por caminhos diferentes.

| o que | como atravessa |
| --- | --- |
| as regras, as skills, as nove barreiras, as páginas | sozinhas: é texto, e a outra ferramenta testada já lê `.agents/skills/` sem configuração nenhuma |
| as cercas que recusam e as que orientam | pela **ponte**, ligada com `python <pasta do clone do atlas>/montar.py --devin --escrever` para o agente de terminal e `--codex --escrever` para o agente sem comando de barra; sem `--escrever`, as duas só ensaiam (`.codex/hooks.json`, mais o espelho dos servidores de contexto em `~/.codex/config.toml`). O Copilot não tem ponte: com a pasta confiada, ele roda direto as cercas do `.claude/settings.json` — medido no CLI |
| a abertura e a parada | no agente sem comando de barra, pela mesma ponte: `SessionStart` e `Stop` do `.codex/hooks.json` |

A ponte não é cerca nova. Ela lê a mesma lista de cercas que o Claude Code lê,
traduz o nome da ferramenta que chegou — os parâmetros já são os mesmos — e
devolve a recusa no dialeto de quem perguntou. Cerca que some daqui some de lá
junto, e ninguém precisa lembrar de dois lugares.

Ela carrega as duas respostas, não só a dura: cerca que **orienta** em vez de
recusar atravessa igual. Essa metade some calada quando ninguém a espera, e
some sem erro nenhum — foi o que aconteceu na primeira versão da ponte.

```bash
python .agents/travessia/travessia.py            # as cercas atravessam?
python .agents/travessia/travessia.py --custa "<pedido>"   # e quanto custa
```

A primeira linha **não abre sessão nenhuma**: ela conversa com a ponte no
dialeto da outra ferramenta e compara com o que a camada deveria responder. É
de graça e se repete quando quiser. A segunda abre duas sessões, com e sem a
camada, e diz a diferença — essa paga, e avisa que paga.

### A bancada dos motores auxiliares

A travessia pergunta se a camada chega ao outro agente. A bancada pergunta o
contrário: se o outro agente serve de **motor auxiliar** para esta sessão —
pesquisa, tarefa somente leitura, ou o papel de crítico.

```bash
python .agents/motores/motores.py --sondar <motor>     # as cinco sondas
python .agents/motores/motores.py --cadastrar <motor>  # sonda e grava
python .agents/motores/motores.py --listar             # o que já foi provado
python .agents/motores/motores.py --credito <motor>    # quanto sobrou
```

São cinco sondas: se responde e está logado, se devolve resultado
estruturado, se a trava de escrita segura, se responde dentro do tempo, e se
o código de saída acusa a tarefa não cumprida. **Só a primeira é de graça** —
as outras abrem sessão no motor e consomem o que ele cobrar, e é por isso que
`--sem-gastar` existe.

Quem reprova é a **trava de escrita**: motor que escreve com a trava ligada
não entra, porque quem o chamar não sabe o que ele garante. As demais viram
**ressalva**, e a ressalva viaja junto com o motor — ela existe para quem vai
chamá-lo.

Duas coisas que a bancada mediu e que valem para qualquer motor. A primeira:
**a trava de escrita não é da mesma natureza em todos** — num motor quem nega
é o sistema operacional, noutro é o próprio agente, e só o primeiro é parede.
A segunda: **o código de saída diz se o processo rodou, não se a tarefa foi
cumprida**. Quem chama confere o resultado; confiar no código de saída trata
tarefa abortada como sucesso.

O `--cadastrar` grava o placar no arquivo local do executor, chave `motores`,
com os papéis do motor, a garantia de escrita, a forma de cobrança, a data da
prova e as ressalvas. **O cadastro é local de propósito**: ele diz o que ESTA
máquina tem e quem está logado nela, e isso não viaja para quem instala a
camada. Data de prova antiga é cadastro envelhecido — o motor muda de versão
e a garantia muda com ele.

O cadastro por si não faz a sessão usar o motor: quem conta a ela o que esta
máquina tem é um gancho de abertura, e quem diz a ela QUANDO despachar é
[Motores auxiliares — quando a sessão despacha, e para quem](motores-auxiliares.md).
O aviso sai do cadastro, então motor novo aparece sem que o gancho mude.

Antes de despachar, `--credito` diz quanto do limite já foi gasto, **sem
gastar chamada**, quando o motor grava isso em disco. Nem todo motor grava:
os que cobram por token não têm fonte local, e aí o instrumento responde
"desconhecido" em vez de inventar número — a diferença importa, porque
estourar um motor de assinatura custa espera e estourar um pré-pago custa
dinheiro.

**O agente sem comando de barra ignora gancho não revisado, em silêncio.**
Com `.codex/hooks.json` escrito e `hooks = true`, a escrita na cópia gerada
passa sem uma linha de log. Ele só roda gancho
que o dono marcou como confiável pelo `/hooks`, por hash da definição, e
gancho que muda pede revisão de novo. Para provar sem o dono, a sessão
não interativa aceita `--dangerously-bypass-hook-trust`, e com ela a
regra 15 barra o `apply_patch` na cópia gerada. O patch chega inteiro em
`tool_input.command`, e a ponte o traduz em uma escrita por arquivo antes
de perguntar às cercas.

**O que ainda não atravessa.** A lista de caminhos negados da outra ferramenta
só vale no arquivo de configuração do usuário, não no do repositório: foi
medido, e é por isso que a ponte usa gancho, que vale no repositório. Quem
quiser a negativa por caminho declara à mão na configuração de usuário.

## O que nunca entra no git

Fora do git ficam a configuração da sua máquina, o resultado das execuções e
o rascunho. Duas linhas que valem por todas:

- **Segredo não entra em git nenhum.** Em texto rastreado vai
  `${VARIAVEL}`, nunca o valor. Vale para repositório privado também.
- **O que nomeia você, sua empresa ou seus outros projetos não viaja.** É o
  que separa a camada — genérica — do seu caso.

O que a sessão precisa e não está no git se declara por nome em
`nucleo/ambiente.json` e se verifica por instrumento. O porquê e a receita
de repor estão em [o estado que não viaja](estado-que-nao-viaja.md).
