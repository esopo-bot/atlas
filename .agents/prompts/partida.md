---
description: O checklist de partida da camada — roda ANTES do briefing, prova item por item que a sessão tem instruções, interpretador, cercas, servidores de contexto, índice, skills e a caixa de ferramentas dos projetos, e devolve como primeira resposta o relatório padronizado de GO, GO DEGRADADO ou NO-GO.
---

# Partida — o checklist antes do briefing

Este é o checklist de partida. Ele vem **antes** do bootstart: o briefing
ensina como se trabalha aqui; a partida prova que a máquina que vai trabalhar
está inteira. Ele não ensina nada e não conserta nada — mede, e devolve um
veredito. Ela roda **sob demanda**, em qualquer agente: quando o dono pede,
ou quando a abertura acusa peça em falta. Não é o primeiro ato de toda
sessão, porque custa caro: a partida inteira leva minutos e muitos tokens
antes de o pedido começar. Os ganchos de abertura e as cercas já guardam o
dia a dia; a partida serve para provar a máquina quando há dúvida, depois
de mudar a camada ou ao estrear um agente. No Claude Code ela é `/partida`.

A forma vem da cabine e do box. Da aviação: fluxo antes, checklist depois;
desafio e resposta; itens que matam primeiro; lista de equipamento mínimo; e
o poll de GO ou NO-GO, uma palavra por posto. Da telemetria de corrida: um
carimbo de tempo só para todas as medições; cada canal com o momento em que
se mede; referência declarada em vez de sensação; alarme com dono; e o rádio
curto, no mesmo formato em toda sessão. O que não foi medido não aconteceu.

## Como se responde

- **Fluxo antes, checklist depois.** O fluxo já existe: a saúde da abertura
  (`camada.py --abertura`), os ganchos de abertura onde há, o `git status`.
  Nenhum item manda executar por executar; cada item confirma que o fluxo
  saiu certo, com o comando rodado e a saída colada.
- **Desafio e resposta.** O desafio é o nome do item, em maiúsculas. A
  resposta é o valor observado, em vocabulário fechado de quatro palavras:
  `PRESENTE <valor>`, `AUSENTE`, `NÃO MEDIDO <motivo>`, `INOPERANTE <desde
  quando, o que fica sem, alternativa, limite>`. "ok", "feito" e
  "confirmado" não são resposta: a linha conta como não respondida.
- **Um item por vez, em ordem, uma chamada de cada vez.** "Itens 1 a 5 ok"
  é bloco, e bloco reprova a fase; script que junta vários itens numa
  chamada só engana a cerca e esconde qual saída é de qual item (medido).
  Chamada em paralelo também reprova: o carimbo tem de vir antes de tudo.
  Item com dois comandos roda os dois em chamadas seguidas; o que reprova é
  juntar itens, não separar comandos.
  Sem saída colada não aconteceu (regra 2). Item que dá negativo pede a
  contraprova na mesma linha: a busca que acha, a recusa com a mensagem.
- **O checklist só lê.** Nenhum item grava, instala ou liga peça. Comando
  que você não achou aqui e parece ensaio pode gravar: medido, as bandeiras
  das pontes do instalador gravam na hora. Na dúvida, não rode, e responda
  NÃO MEDIDO.
- **Os comandos rodam em qualquer shell.** São `git`, `python` e `ls`. O
  `ls` só mostra; toda contagem é em `python`, porque no PowerShell o `ls`
  conta arquivo de ponto e muda o número (medido). Se o seu shell não tiver
  um deles, traduza e diga na linha que traduziu. **A sonda do item 7 nunca
  se traduz:** `cd` e `cat` existem em toda concha, também como apelidos no
  PowerShell, e a cerca só conhece a forma literal. Traduzida para
  `Set-Location` e `Get-Content`, ela passa pela cerca e mede nada (medido).
- **NÃO MEDIDO nunca vira GO.** Em item que mata, NÃO MEDIDO é NO-GO. Em
  item da lista de equipamento mínimo, entra no GO DEGRADADO pelo nome e
  pelo motivo. Sessão sem cabeça, sem comando de barra ou sem gente no
  terminal mede pelo efeito: todo item abaixo tem uma prova que não depende
  de comando de barra. Responder de cor é o erro que este checklist existe
  para impedir.
- **Que sessão é esta.** Sessão que escreve é a que vai mudar arquivo,
  commitar, mesclar ou postar. Sessão de pesquisa tem a marca
  `ATLAS_SO_LEITURA`, ou um pedido que só lê, como pedir só este checklist.
  O tipo sai do pedido e vai na linha 1 do relatório.
- **Itens que matam.** Raiz errada, interpretador que não é 3, autorizações
  não lidas, cercas mortas em sessão que vai escrever, endereço das issues
  ausente em sessão que vai postar, branch de longa duração como alvo de
  commit. Qualquer um deles é NO-GO: a sessão para no passo que a falta
  impede e escreve a razão.
- **Lista de equipamento mínimo.** Índice, servidor de contexto opcional,
  conector do cliente, perfil de navegador, postagem no rastreador e ponte
  por agente podem seguir INOPERANTES — só com as quatro coisas na linha:
  desde quando, o que fica sem (a skill ou o passo que dependia), a
  alternativa nomeada, e o limite (esta sessão). Faltou uma, é NO-GO.
- **Veredito em uma linha**, vocabulário fechado: `GO`; `GO DEGRADADO em
  <n> item(ns): <nomes>`; `NO-GO em <item>: <o passo que a falta impede>`.
- **Quem age no vermelho** vem na linha: a sessão conserta e prova; o dono
  decide, e o item vira a pergunta única no começo da resposta, com o link
  do que espera por ele; ou o gancho recusa, e a recusa é a prova.
- **Interrupção.** Interrompido no item N, a resposta é "partida parada no
  item N"; atende, e retoma repetindo o N. Perdeu o lugar (contexto
  comprimido): refaz a fase inteira. Toda sonda daqui é repetível sem custo.
- **O vocabulário e a lista dos que matam só mudam por decisão do dono**,
  com data e motivo (regra 20). Item novo entra só se for crítico, costumar
  ser esquecido, não ter gancho que já o cubra e ter resposta específica.

## Fase 1 — PARTIDA: o motor

Roda uma vez, antes de qualquer outro comando. Os comandos supõem a raiz (a
pasta com o `AGENTS.md`) como diretório atual, como o briefing supõe.

| n | desafio | comando | resposta esperada | se falhar, quem age |
| --- | --- | --- | --- | --- |
| 1 | CARIMBO | `python -c "import datetime, os; print(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'SO_LEITURA=' + os.environ.get('ATLAS_SO_LEITURA', ''), 'ETAPA=' + os.environ.get('ENCADEADOR_ETAPA', ''))"` | um carimbo só, que vai na linha 1 do relatório. Marca vazia liga o conjunto comum; `ATLAS_SO_LEITURA` liga o de pesquisa (escrita fechada); `ENCADEADOR_ETAPA` liga o de etapa do executor (política fechada) | informativo: linha sem carimbo não se compara com nada |
| 2 | INTERPRETADOR | `python -c "import sys; print(sys.version_info[0])"` | `3`. `which` e o nome `python3` não são prova: no Windows `python3` pode ser o atalho da loja, que está no PATH e não roda | NO-GO: nenhum instrumento abaixo vale; a sessão conserta antes |
| 3 | RAIZ | `git rev-parse --show-toplevel` e `ls AGENTS.md` | a raiz do git igual ao diretório atual, e o `AGENTS.md` listado. Em subpasta a sessão roda sem skill nem gancho da raiz e nada avisa (regra 1) | NO-GO: reabra na raiz |
| 4 | ABERTURA | `python .agents/camada/camada.py --abertura` | `Abertura íntegra: 4 peça(s) de pé.` As quatro peças, cada uma PRESENTE ou AUSENTE: instruções, servidores declarados, endereço do quadro, índice. Duas ausências não são falta: repositório sem servidor e sem módulo do índice abrem íntegros | peça AUSENTE vai na primeira resposta, sem chute; as três últimas se destrincham nos itens 6, 10 e 13 |
| 5 | AUTORIZAÇÕES | `python -c "import json; print(json.load(open('nucleo/configuracao.json', encoding='utf-8'))['autorizacoes'])"` | os três valores citados: commit, push, publicar. Omissão não é permissão (regra 9) | NO-GO para sessão que vai commitar ou publicar sem os ter lido |
| 6 | QUADRO | `python .agents/camada/camada.py --quadro` | o endereço `dono/repositório` onde toda issue nasce, mesmo a de código que mora em outro lugar. Em relatório que vai para arquivo rastreado, `PRESENTE <quadro>` sem o valor: o repositório da camada é público | `nucleo/executor.json` é local e não viaja para worktree nem nuvem: AUSENTE, declarado. NO-GO só no passo que posta: issue, relato, linha do quadro |
| 7 | CERCA VIVA | `cd nucleo; cat regras.json`, literal, sozinho, numa chamada só | RECUSADO, com a mensagem da regra 1 inteira. Passou e imprimiu o arquivo: as cercas não estão nesta sessão. Só a recusa prova que a linha do gancho achou o Python e a raiz, que o despachante subiu e que a cerca carregou; a sonda enterrada num script com outros itens passa sem ser vista | NO-GO para sessão que escreve, commita ou mescla (regra 9 sem guarda); informativo na sessão que só pesquisa |
| 8 | GANCHOS DESTA SESSÃO | `git log -1 --format='%cI %h' -- .claude/settings.json .claude/hooks .codex .devin` | data anterior ao carimbo do item 1. Gancho novo só carrega em sessão nova, e nada avisa | data posterior: NÃO MEDIDO, reabra a sessão |
| 9 | ÁRVORE | `git status --short; git branch --show-current; git worktree list` | os três valores citados. Sujeira que você não fez é outra sessão viva: não commite, não apague, não conserte. Repete-se antes de todo `git` | NO-GO para commit se a branch atual for de longa duração (`branches_por_incorporacao`); na partida é informativo |

Última linha da fase, literal: `PARTIDA COMPLETA`. Sem ela a fase não vale.

## Fase 2 — CAIXA: as ferramentas

Roda antes de abrir o primeiro arquivo do pedido. É o inventário do que a
sessão tem à mão, provado peça a peça: nascer sabendo o que há na caixa é o
que evita procurar um navegador que já está declarado, ou prometer um
conector que não existe neste agente.

| n | desafio | comando | resposta esperada | se falhar, quem age |
| --- | --- | --- | --- | --- |
| 10 | SERVIDORES | para cada servidor que o `.mcp.json` declara, uma chamada barata que só lê: quem sou, listar abas, estado de um alvo do índice (o caminho do alvo, não a raiz: pela raiz ele responde "não indexado" e mente) | declarado é o que o item 4 listou; vivo é o prefixo do servidor na sua lista de ferramentas mais a primeira linha da resposta colada. Sem chamada, NÃO MEDIDO: o cliente não guarda em disco quem conectou, e token vencido lista ferramentas e falha na primeira chamada | `INOPERANTE <nome> desde <hora>, sem <o que dependia>, alternativa <busca sem servidor, gh, túnel>, limite esta sessão`. NO-GO só quando o pedido depende dele |
| 11 | CONECTORES | a lista de ferramentas do cliente: e-mail, arquivos, notas, agenda; e uma chamada barata que só lê em cada um que aparecer (listar etiquetas, listar calendários) | conector conta só com a chamada respondida, em qualquer agente. No Claude Code a ferramenta de estado dos conectores da sessão já traz cada um com estado. Agente sem conector nenhum: `AUSENTE (não existe neste agente)`, dito na primeira resposta, antes de o dono pedir. Conector que aparece na lista e não foi chamado é NÃO MEDIDO, nunca PRESENTE: medido, uma sessão afirmou "presentes" sem chamar nenhum | vira INOPERANTE só quando o pedido nomeia o conector: `alternativa: o dono envia ou cola` |
| 12 | NAVEGADOR | o servidor de navegador do `.mcp.json` e os perfis salvos: `ls .credenciais/playwright` | o servidor vivo por uma chamada que lista abas, e os NOMES dos perfis, nunca o conteúdo. A receita de tela de cada vizinho mora no perfil dele em `conhecimento/projetos/`. A pasta de perfis é local e não viaja para worktree nem nuvem: lá, AUSENTE declarado | pedido de tela com navegador INOPERANTE ou perfil ausente: NO-GO para dar por pronto, porque a régua do pronto inclui abrir a tela |
| 13 | ÍNDICE | `python .agents/indice/indexar.py --estado`, depois a contraprova `python .agents/indice/buscar.py "<termo do pedido>" --alvo <alvo do pedido> --quantos 3`; sem pedido ainda, `--alvo conhecimento` e um termo que existe na camada, como `regra 16` | `LIGADO`, as duas portas respondendo, a linha de falhas, e três trechos com caminho e linha. O alvo é uma chave de `.agents/indice/alvos.json`, nunca `.`: vizinho fora da lista devolve vazio, e vazio não é ausência. Em worktree o alvo resolve para a pasta da worktree, que a ronda não indexou: INOPERANTE esperado, e a busca vale na raiz principal. Não busque durante a ronda | `INOPERANTE índice para <alvo>, sem a busca por significado, alternativa grep -rn, limite esta sessão`; alvo que falhou na ronda ou está fora da lista vai ao dono com a linha do `--estado` |
| 14 | SKILLS | `python -c "import os; pastas = lambda p: sorted(d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))); print(pastas('.agents/skills')); print(pastas('.claude/skills'))"`, contra a lista que o seu agente carregou | as duas listas iguais, só pastas, e a sua lista com todas as da pasta que o seu agente lê (seção por aeronave). Dois-pontos na descrição invalida a skill em silêncio | falta uma: degradado, nomeando qual. Lista vazia: raiz errada, volte ao item 3 |
| 15 | CÓPIA | na casa da camada, `python montar.py --verificar`; numa instalação, `python <pasta do clone do atlas>/montar.py --verificar`, rodado daqui | na casa, `Tudo em dia — nada a sincronizar.`; numa instalação, `A camada instalada aqui está em dia com a origem.` Editou a fonte, regenere e prove (regra 15) | degradado na partida; obrigatório verde antes de entregar |
| 16 | AMBIENTE | `python -c "import json, shutil; d = json.load(open('nucleo/ambiente.json', encoding='utf-8')); print({c: bool(shutil.which(c)) for c in d['comando'] + ['python', 'npx', 'docker']})"` e `python -c "import os, re; t = open('.mcp.json', encoding='utf-8').read(); print({v: v in os.environ for v in sorted(set(re.findall('[$][{]([A-Za-z0-9_]+)[}]', t)))})"` | só `True` nos dois: cada comando que `nucleo/ambiente.json` declara, mais os três de que índice e navegador dependem, para o ambiente que ainda não os declara, e cada variável que o `.mcp.json` pede, por NOME. Nome se verifica; valor nunca se imprime | peça `False`: INOPERANTE no item que dela depende; sem `git` em sessão que commita é NO-GO |
| 17 | REGRA POR CAMINHO | `ls .claude/rules` | a regra do padrão de código, que o Claude Code carrega ao abrir arquivo de código. Nos outros agentes, `AUSENTE (não existe neste agente)`: lá o padrão chega pela skill `padrao-de-codigo`, invocada | informativo |

Última linha da fase, literal: `CAIXA COMPLETA`.

## Por aeronave

Cada agente mede os mesmos 17 itens; muda o instrumento e a armadilha. A
seção do seu agente substitui só o que ela nomeia.

### Claude Code

- Chegada: `/partida`, quando o dono pede. Os ganchos de abertura já rodaram
  o fluxo: os avisos de ambiente, servidor e índice aparecem no transcript,
  ou o silêncio deles.
- Item 3: os ganchos leem a raiz por `CLAUDE_PROJECT_DIR`, que existe só no
  ambiente deles, não no terminal da sessão; `echo` dele vazio não é falta.
  A prova de que gancho e sessão olham a mesma raiz é a recusa do item 7.
- Item 7: `/hooks` lista as matrículas; `claude doctor` nomeia arquivo de
  configuração rejeitado. A prova continua sendo a recusa.
- Itens 10 e 11: no aplicativo, a ferramenta de estado dos conectores da
  sessão; no terminal, os prefixos `mcp__` na lista de ferramentas, com
  conector como `mcp__claude_ai_<nome>__`.
- Item 14: `/skills` contra a lista de `.claude/skills` do item 14; comando
  de barra aparece como skill a mais. Sem cabeça (`claude -p`, subagente) não há barra: vale
  o efeito.
- Item 17: `/context` mostra a regra depois de abrir um arquivo de código.

### Codex

- Chegada: quando o dono pede, pelo nome do arquivo. Prompt customizado está descontinuado
  na ferramenta; a forma de chegar é instruções mais skills. No Windows os
  comandos rodam em PowerShell: por isso o checklist só usa `git`, `python`
  e `ls`, e a sonda do item 7 vai sozinha, nunca dentro de um script.
- Item 7: a recusa da sonda, quando vem, prova tudo de uma vez: raiz
  confiada, ponte carregada, cerca viva. Só quando a sonda PASSA a suspeita
  tem ordem: primeiro `grep -B1 -A1 trust_level ~/.codex/config.toml`, que
  tem de mostrar esta raiz como `trusted`, porque projeto não confiado ignora
  a pasta `.codex/` inteira, configuração e ganchos, em silêncio; depois a
  confiança dos três ganchos de `.codex/hooks.json`, porque gancho que o dono
  não revisou é ignorado sem linha de log. Ela se dá só pelo `/hooks` do Codex
  de terminal: o aplicativo de mesa não tem esse comando. Fica em
  `~/.codex/config.toml`, uma entrada por gancho em `[hooks.state]` com o
  hash do arquivo, e vale também para o aplicativo de mesa (medido). Mudou o
  `.codex/hooks.json`, a confiança se dá de novo. Só o
  dono confia.
- Item 8 soma `python <pasta do clone do atlas>/montar.py --codex` (ensaio): o espelho do `.mcp.json`
  em `~/.codex/config.toml` tem de estar em dia. `codex mcp list` mostra
  declaração; vivo é a chamada do item 10.
- Item 14: `/skills` contra a lista de `.agents/skills` do item 14: o Codex
  lê a fonte, não a cópia.
- Item 10: no aplicativo de mesa, os comandos passam por uma ferramenta de
  execução, e os servidores ficam no objeto `tools` dela, com nomes
  `mcp__<servidor_com_sublinhado>__<ferramenta>`. Procure ali antes de dizer
  que servidor nenhum está disponível: quem não procura ali diz "nenhum"
  com todos vivos. Sem cabeça, `codex exec` só chama ferramenta
  de servidor aprovada: `-c 'mcp_servers.<nome>.tools.<ferramenta>.approval_mode="approve"'`
  libera uma só, sem soltar shell nem escrita.
- Item 11: o aplicativo pode trazer conectores próprios como ferramenta;
  conta só o que respondeu a uma chamada barata, e sem chamada é NÃO MEDIDO. Item 12: navegador e voz: `codex features list` mostra
  `browser_use` e `in_app_dictation` com `stable true`; a conversa por voz
  existe só no aplicativo de mesa, é outra peça, e o ditado só transcreve o
  pedido.

### Devin

- Chegada: quando o dono pede, pelo nome do arquivo. Na nuvem `nucleo/executor.json` não
  existe, porque não entra no git: item 6 AUSENTE, declarado.
- `devin rules list`, `devin skills list` e `devin mcp list` são inventário
  do disco, não prova de carga; a prova é o efeito, nos itens 7, 10 e 14.
- Item 7: `.devin/hooks.v1.json` presente é ponte ligada; ausente, as
  cercas não valem aqui, e escrita segue só com o dono no terminal. Ligar a
  ponte é decisão do dono: `python <pasta do clone do atlas>/montar.py
  --devin` só ensaia, e com
  `--escrever` monta a camada na pasta e liga a ponte. Na nuvem os ganchos
  falham abertos por desenho: nunca contam como muro.
- Sem cabeça (`devin -p`), a recusa do item 7 encerra a sessão antes do
  relatório (medido). Ali não rode a sonda: responda NÃO MEDIDO, e a prova
  de fora é `python .agents/travessia/travessia.py`, que manda as sondas à
  ponte sem abrir sessão. No plano gratuito o `devin -p` só roda comando sem
  aprovação com `--permission-mode dangerous`, que também libera escrita:
  ali a ponte é a única guarda.
- Item 14: lê `.agents/skills` e `.devin/skills`, não `.claude/`.
- Item 11: conector só com chamada respondida; sem nenhum na lista, AUSENTE.
  Item 12: o navegador é o do próprio agente, e a prova é a captura de tela
  com a URL visível.

### Copilot, no editor e no terminal

- Chegada: quando o dono pede, pelo nome do arquivo; o `AGENTS.md` só a
  aponta. No editor a leitura do `AGENTS.md` depende da configuração
  `chat.useAgentsMdFile`; a lista de instruções do chat mostra o arquivo
  carregado. No terminal, `/instructions`.
- Item 7: com a pasta confiada, o Copilot roda direto as cercas do
  `.claude/settings.json`, sem ponte: ele entrega `CLAUDE_PROJECT_DIR` no
  ambiente e a entrada no formato do Claude (medido no CLI oficial). A
  recusa da sonda prova tudo. Sem recusa, a primeira suspeita
  é a pasta fora de `trustedFolders` em `~/.copilot/config.json`: pasta não
  confiada não carrega gancho nenhum do repositório, em silêncio, e o item é
  INOPERANTE, com escrita só com o dono no terminal.
- Item 10: o Copilot traz um servidor próprio do GitHub embutido, que não é
  o `github` declarado: chamada nele não prova o declarado. Medido no
  `copilot -p` sem a pasta confiada: os servidores do `.mcp.json` não
  subiram, então cada um é NÃO MEDIDO. No editor ele lê `.vscode/mcp.json`, que a camada não gera: pode
  abrir sem servidor nenhum, AUSENTE, declarado.
- Item 14: lê `.github/skills`, `.claude/skills` e `.agents/skills`: contagem
  em dobro é skill duplicada, achado para o dono, não falta. Comando de barra
  de `.claude/commands/` pode aparecer como skill a mais: também não é falta.
- Item 11: conector só com chamada respondida; sem nenhum na lista, AUSENTE.

## O relatório

É a primeira resposta da sessão, no lugar do molde "A primeira resposta da
sessão" do briefing, que ele estende. Rádio curto: mesmo formato em toda
sessão, número só ao lado do comando que o produziu. `cabeça` é `sim` quando
há gente no terminal para responder a uma pergunta; é `não` em `claude -p`,
`codex exec`, `devin -p`, `copilot -p`, subagente e roteiro do executor.

```
PARTIDA <carimbo> · agente <claude|codex|devin|copilot> · cabeça <sim|não> · conjunto <comum|pesquisa|etapa> · sessão <escreve|pesquisa>
| n | desafio | comando | saída colada | resposta | quem age |
| 1 | CARIMBO | python -c ... | 2026-09-15T12:00:00Z | PRESENTE | ninguém |
| ... | | | | | |
PARTIDA COMPLETA
| 10 | SERVIDORES | ... | ... | PRESENTE 4 de 5; INOPERANTE <nome> desde <hora>, sem <o que dependia>, alternativa <...>, limite esta sessão | dono |
| ... | | | | | |
CAIXA COMPLETA
Veredito: GO DEGRADADO em 1 item: SERVIDORES
O que faltou: <prova que não rodou, cerca que barrou, peça ausente; ou "nada">
Espera por você: <o item cuja decisão é do dono, com o link; ou "nada">
```

Depois do veredito vem o briefing: leia `.agents/prompts/bootstart.md`
inteiro e diga, em uma linha, qual caminho da tabela dele o pedido segue. O
relatório e essa linha abrem a primeira resposta, e **não a encerram**: com
GO ou GO DEGRADADO, o pedido do dono é atendido na mesma vez, logo abaixo.
Parar no relatório deixa o dono sem o que pediu (medido). Relatório colado em
issue ou comentário leva a mesma tabela; em arquivo rastreado, sem o valor
do quadro nem nome de conta.

## Depois da partida

- `GO` ou `GO DEGRADADO`: siga para o briefing e atenda o pedido na mesma
  resposta, sem esperar o dono dizer "continue".
- `NO-GO`: pare no passo que a falta impede, escreva a razão, e faça o que
  não depende dela. Item que é do dono vira a pergunta única no começo da
  resposta, com o link. Relatar não é pedir licença (regra 19).
- Defeito da camada que a partida revelou não se conserta na sessão: vira
  linha do quadro por `python .agents/caixa/caixa.py defeito --id <kebab>
  --assunto "..."`, com o número citado no relato.

## Prova de leitura: quando o pedido é provar que o agente lê a camada

A partida prova que as peças estão de pé. Quando o dono pede mais — que o
agente mostre que **lê** as instruções e as skills —, a sessão segue estes
passos depois do relatório, com saída colada, ou diz exatamente o que não
enxerga.

1. **Skills.** O item 14 já comparou a sua lista com a pasta que o seu agente
   lê. O que está na pasta e não apareceu na sua lista é skill que você NÃO
   lê. Se a cópia e a fonte divergem, é defeito de sincronização, não de
   leitura: o item 15 acusa.
2. **Responda sem abrir arquivo:** quais são as nove barreiras do portão da
   camada, na ordem? Só depois abra `.agents/skills/portao/SKILL.md` e
   confira. Acertou os nove nomes na ordem: você leu a skill. Inventou ou
   pulou: não leu. Diga qual foi.
3. **Responda sem abrir arquivo:** o que este repositório manda fazer antes
   de criar algo novo, e quem pode publicar? Depois abra `AGENTS.md` e
   confira. "Procurar e citar o que já existe" e "publicar é do dono" são as
   respostas que provam a leitura.
4. **Diga de onde você lê instrução e skill** — o nome exato dos arquivos e
   pastas que o seu agente carrega neste repositório, pela seção do seu
   agente acima. Se você não sabe, diga "não sei", nunca chute.
5. **Repita 2 e 3 numa conversa nova**, porque uma medição não é medição: a
   escolha de skill varia entre conversas.

A entrega é uma tabela, colada num comentário da issue que pediu a prova:

| passo | resultado | prova colada |
| --- | --- | --- |
| skills que enxergo | N de M da pasta | as duas listas do item 14 |
| barreiras do portão | acertei / errei em ... | a resposta antes de abrir |
| ordem do AGENTS.md | acertei / errei em ... | a resposta antes de abrir |
| de onde leio | arquivos e pastas | a lista, ou "não sei" |
| repetição | igual / diferente em ... | a segunda rodada |

E um veredito em uma linha: **leio os dois**, **leio só as skills**, **leio só
o AGENTS.md** ou **não leio nenhum**. Onde não ler, o que faltou, com nome:
arquivo que o agente não carrega, configuração que falta, política que barra.
Nada de suposição. A prova não instala nada, não muda configuração e não edita
a camada: o que barrar é achado para o dono, com a mensagem exata.

## De onde vem a forma

Resumo próprio; o texto de cada fonte fica no endereço.

- Fluxo antes e checklist depois, desafio e resposta, itens críticos
  primeiro, a frase que fecha a fase e a lista dos erros clássicos: FAA,
  Advisory Circular 120-71B
  (<https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-71b.pdf>),
  e Degani e Wiener para a NASA, "Human Factors of Flight-Deck Checklists"
  (<https://www.faa.gov/sites/faa.gov/files/2022-11/NASA%20Ames%20Rpt%20CR%20177549%20.pdf>).
- Chamadas padronizadas com vocabulário fechado, e a interrupção que retoma
  pelo item: Flight Safety Foundation, ALAR Briefing Notes 1.4 e 1.5
  (<https://flightsafety.org/wp-content/uploads/2016/09/alar_bn1-5-checklists.pdf>).
- Lista de equipamento mínimo, que despacha com item inoperante declarado, e
  o que nunca pode estar inoperante: 14 CFR 91.213
  (<https://www.law.cornell.edu/cfr/text/14/91.213>) e AC 91-67A.
- O poll de GO ou NO-GO, uma palavra por posto, e a lista de parâmetros com
  limite amarelo e vermelho: NASA, controle de lançamento da Artemis
  (<https://www.nasa.gov/wp-content/uploads/2024/06/ops-cept-001-mod-ii-go-nogo-rev-508.pdf>).
- Tabelas de registro por canal, carimbo de tempo único e sincronização de
  fontes: especificação técnica da unidade de controle padrão da FIA
  (<https://legal.fia.com/web/appeloffre.nsf/2A59DE0C92F81BE5C12587E6004401A6/$FILE/Appendix1_TechnicalSpecifications.pdf>).
- Declaração assinada antes da primeira sessão de pista, e a volta de
  instalação que atravessa tudo de ponta a ponta antes do trabalho real:
  regulamento esportivo da Fórmula 1 de 2026, artigo B3.1
  (<https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_05_-_2026-02-27.pdf>),
  e o glossário oficial dos testes de pré-temporada
  (<https://www.formula1.com/en/latest/article/from-aero-rakes-to-flow-vis-5-key-terms-you-need-to-know-for-f1-pre-season-testing.7gcryzPYiJAm1FqJGIrC9u>).
