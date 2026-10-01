# O que vive fora do repositório

Parte do que muda o comportamento de uma sessão não está no git. Mora no
settings do usuário, no settings local da raiz, no agendador do sistema, no
PATH e na pasta `tmp/`. Clone novo não traz nada disso, e a falta não dá
erro: a sessão só trabalha com menos. Esta página diz o que cada peça faz e
como repor numa máquina nova.

O porquê dessa categoria, e como declarar por nome o que a sessão exige,
está em [o estado que não viaja](estado-que-nao-viaja.md). Aqui mora a lista.

| Peça | Onde mora | O que muda na sessão |
| --- | --- | --- |
| telemetria OTLP | settings do usuário | custo, tokens e eventos chegam ao destino |
| etiquetas por raiz | `.claude/settings.local.json` | o destino separa repositório e frente |
| classificador do modo automático | settings do usuário | o que o modo automático nega |
| manutenção agendada | agendador do sistema | a abertura deixa de buscar |
| `gitleaks` e `codex` | fora do repositório | publicar e despachar |
| registro de negativas | `tmp/` da árvore principal | o que o classificador negou |
| comando da revisão periódica | checkout principal, fora do git | o `/revisar-atlas` existe |
| relatório do `/insights` | perfil do usuário | a revisão lê os atritos |

Nesta página, `${NOME}` marca o que você preenche. Nenhum valor mora aqui.

## A telemetria, no settings do usuário

O Claude Code exporta métrica e evento por OpenTelemetry, sem agente nem
coletor no caminho. As variáveis vão no bloco de variáveis (`env`) do
settings do usuário, e valem para toda sessão da máquina:

| Variável | O que faz |
| --- | --- |
| `CLAUDE_CODE_ENABLE_TELEMETRY` | `1` liga a telemetria; sem ela nada sai |
| `OTEL_METRICS_EXPORTER` | `otlp` exporta métrica: custo, tokens, sessão |
| `OTEL_LOGS_EXPORTER` | `otlp` exporta evento: erro de API, gancho, servidor |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | `${ENDERECO_OTLP_DE_METRICAS}` |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | `${ENDERECO_OTLP_DE_LOGS}` |
| `OTEL_EXPORTER_OTLP_METRICS_PROTOCOL` | `http/protobuf` |
| `OTEL_EXPORTER_OTLP_LOGS_PROTOCOL` | `http/protobuf` |
| `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | `delta`, para destino que só aceita delta |
| `OTEL_METRIC_EXPORT_INTERVAL` | intervalo de envio da métrica, em milissegundos |
| `OTEL_LOGS_EXPORT_INTERVAL` | intervalo de envio do evento, em milissegundos |
| `OTEL_LOG_TOOL_DETAILS` | `1` põe no evento o comando, o caminho e o nome da skill |

A chave do destino **não** vai no bloco de variáveis. O bloco entrega o
texto cru: `${CHAVE_DO_DESTINO}` chega como está, o destino recusa o
cabeçalho, e nada aparece no terminal. A chave vai pelo `otelHeadersHelper`,
uma chave do próprio settings que aponta um programa fora do repositório:
`"otelHeadersHelper": "${CAMINHO_DO_AJUDANTE}"`. O programa lê a chave do
ambiente na hora e imprime o JSON dos cabeçalhos. Ele só vale com protocolo
`http/protobuf` ou `http/json`, e roda de novo de tempos em tempos. O
endereço vai por extenso no settings: ele não é segredo, e o bloco não o
expandiria.

O `OTEL_LOG_TOOL_DETAILS` tem preço: o texto dos comandos, os caminhos de
arquivo e a entrada das ferramentas passam a morar no destino. Ligue só se o
destino é seu e se a investigação precisa do comando exato.

A telemetria sobe na largada. Sessão já aberta não pega a mudança.

## O que as etiquetas por raiz acrescentam

Estas vão no bloco de variáveis do `.claude/settings.local.json` da raiz, e
valem só nas sessões abertas nela:

- `OTEL_METRICS_INCLUDE_REPOSITORY=true` põe em cada métrica e evento a
  identidade do repositório da sessão: `vcs.repository.name`,
  `vcs.owner.name`, `vcs.repository.url.full` e `vcs.provider.name`. É o que
  deixa o destino somar o custo por repositório.
- `OTEL_RESOURCE_ATTRIBUTES=service.name=${NOME_DA_FRENTE}` põe uma etiqueta
  sua em toda métrica e evento. O formato é `chave=valor` separado por
  vírgula, sem espaço.
- `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` liga os spans:
  `claude_code.interaction`, `claude_code.llm_request`, `claude_code.tool` e
  os filhos dele. Cada span de subagente leva `agent_id` e
  `parent_agent_id`, e a sessão principal vai sem os dois: é o que separa o
  custo do subagente do custo da sessão.

**Os spans só saem com exportador de traces e endereço.** Faltam
`OTEL_TRACES_EXPORTER=otlp` e `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` com
`${ENDERECO_OTLP_DE_TRACES}`, ou o endereço comum
`OTEL_EXPORTER_OTLP_ENDPOINT`. Quem exporta só métrica e evento, como a
receita acima, liga o beta e não recebe span nenhum. Antes de procurar span
no destino, confira os nomes no settings.

## O classificador do modo automático

O modo automático tem um classificador que decide o que a sessão roda sem
perguntar. A configuração dele, `autoMode`, só vale no settings do usuário:
o settings do projeto não a carrega, e por isso ela não viaja no git.

- `autoMode.environment` é uma lista de frases que descrevem o ambiente ao
  classificador. Cada frase é um fato: a visibilidade do repositório e para
  onde vai o que é rastreado; qual é o repositório e a pasta de trabalho
  confiáveis; o controle de versão e as branches protegidas; os domínios e
  serviços internos confiáveis; onde mora dado sensível e quem pode vê-lo;
  as ferramentas de linha de comando da casa. O que não se aplica fica como
  "nenhum configurado", no molde que o próprio comando mostra.
- O fato que mais pesa é para onde vai o que é rastreado: repositório
  público, privado, ou privado com espelho público. Declare-o numa entrada
  própria da lista. Se algum desses destinos é público, o classificador
  precisa tratar todo o conteúdo rastreado como público.
- `autoMode.soft_deny` guarda as negativas próprias. A entrada `$defaults`
  mantém as regras de fábrica, e as suas se somam a elas.

Conferir: `claude auto-mode config` mostra a configuração em vigor, e
`claude auto-mode critique` revisa as regras próprias atrás de regra
ambígua. É configuração de segurança: a sessão prepara o trecho exato e o
dono aplica.

## O settings local da raiz

O `.claude/settings.local.json` é da máquina: fora do git, e a atualização
da camada não o reescreve. Além das etiquetas acima, ele guarda as
permissões pessoais, os servidores de contexto liberados e os ganchos que só
esta máquina tem. O `MCP_TIMEOUT`, o tempo que a sessão espera um servidor
de contexto subir, também mora nele, para quem tem servidor MCP lento;
nenhum servidor da camada precisa dele hoje. O que cada campo faz e como
provar que o arquivo se lê está em
[o par de settings](verificacao-pos-atualizacao.md). Worktree nova e clone
novo nascem sem ele: copie da raiz.

## A manutenção agendada

```bash
python .agents/camada/camada.py --agendar
```

O comando **só imprime**: não registra nada. Ele mostra a linha que agenda o
`--manutencao` uma vez por dia, no agendador de tarefas do Windows ou no
`crontab` fora dele, e as linhas de conferir, rodar agora e remover. A
manutenção busca a integração, os vizinhos, o histórico e o índice, e grava
a marca `tmp/manutencao-noturna.json`. A abertura que acha marca recente não
busca de novo.

Registrar a tarefa é configuração persistente da máquina: pede o sim do
dono. A tarefa é do usuário e roda com ele logado; máquina dormindo na hora
pula o dia, e a abertura seguinte busca como sempre.

## Os binários que alguma peça chama

- `gitleaks`: a segunda rede de segredo do `publicar.py`, procurada no
  PATH. Sem ele, o ensaio avisa e segue só com a expressão regular própria,
  e a publicação de verdade recusa. Instale pela página de versões do
  projeto, confira o SHA-256 no arquivo de somas da mesma versão e ponha a
  pasta no PATH. Quem quer o aviso na abertura declara o nome em
  `nucleo/ambiente.json`.
- `codex`: o agente de terminal a quem a peça de despacho manda trabalho.
  No Windows ela o procura na pasta de aplicativos do usuário, onde o
  instalador oficial o põe, e não no PATH: instalar por outro caminho não
  basta.

## O registro de negativas

Cada negativa do classificador vira uma linha em
`tmp/negativas-do-classificador.jsonl`, gravada pelo gancho de
`PermissionDenied` da camada. A linha leva a ferramenta e o comando exato,
com o segredo mascarado pelo detector do histórico; sem o detector, o
comando não é gravado. Sessão em worktree grava na árvore principal, porque
o `tmp/` da worktree some com ela. O arquivo fica fora do git: máquina nova
começa com o registro vazio.

## O comando da revisão periódica

O roteiro é um prompt fixo, disparado por um comando de barra local, que
uma sessão segue do começo ao fim. Ele guarda as decisões que não se
rediscutem e manda medir antes de opinar: rodar as rotinas de verificação
do repositório, a bancada e a simulação de uma sessão de verdade. Responde
a uma lista fixa de perguntas, cada uma com evidência de comando: o que
ainda é instrução e podia virar instrumento, o que custa e não rende, o
que envelheceu e o que dá para tirar. Aplica uma régua que separa proposta
de opinião, define o pronto e diz como executar pela esteira. Termina com
o relatório da rodada, a fila da arquitetura e a tabela da última medição,
que a própria rodada atualiza.

O comando de barra em `.claude/commands/` e o procedimento em `execucoes/`
são arquivos locais, listados no `.git/info/exclude`. Numa máquina nova,
escreva os dois de novo a partir desta descrição, sem copiar o original.
O comando de barra só aponta para o procedimento e lembra de rodar os
comandos que a prosa manda, rodar a simulação e procurar lá fora uma vez
por rodada. O procedimento reúne as decisões, medições, perguntas, régua,
pronto, esteira e saídas descritas acima. Registre a primeira medição como
linha zero da tabela. Esses textos ficam na máquina, fora do git.

O `/insights` roda uma vez por semana, na sessão interativa, antes da
rodada de revisão. Grava o relatório em `~/.claude/usage-data/report.html`,
com uma cópia datada ao lado. Analisa só as sessões desta máquina, gasta
cota, e o relatório some com as transcrições, no prazo que
[o estado que não viaja](estado-que-nao-viaja.md) ensina a alargar. Os
atritos que aponta entram na rodada como hipóteses a medir, nunca como
contagens: os números vêm da telemetria.

## Numa máquina nova, na ordem

1. No settings do usuário: a telemetria, o ajudante de cabeçalho e o prazo
   das transcrições. O `autoMode`, o dono aplica.
2. Clone e settings local da raiz, pela receita do par de settings.
3. `gitleaks` no PATH e o `codex` pelo instalador oficial.
4. `--agendar`, e o dono registra a tarefa.
5. Refaça o comando e o procedimento pela seção da revisão periódica;
   inclua o `/insights` semanal na agenda.
6. Sessão nova: `python .agents/camada/camada.py --abertura`,
   `claude auto-mode config`, e a primeira métrica chegando ao destino com o
   nome do repositório.
