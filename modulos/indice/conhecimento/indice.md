# O índice de código

Busca por significado no código dos repositórios: a sessão pergunta "onde a
autenticação decide quem entra" e recebe o trecho, sem depender de acertar a
palavra que o autor usou. Chega pelo módulo `indice`
(`python montar.py --modulo indice`); o cartão do módulo diz como subir.

## Quando ele vale a pena — a régua medida

Índice cobra manutenção e disco; `grep` é de graça. A régua, medida em
31/08/2026 sobre um workspace real de 10 repositórios:

- Abaixo de ~2 mil arquivos rastreados, o `grep` ganha — o acervo cabe em
  poucas varreduras.
- Acima de ~10 mil, o índice ganha claro — foi o caso de um único repositório
  de referência do workspace medido.
- No meio, decida pela dor: se as sessões varrem o mesmo repositório várias
  vezes por pergunta, o índice se paga.

Conte os arquivos antes de instalar:

```bash
git ls-files | wc -l
```

## As peças, e a regra que governa

| Peça | O quê | Onde |
| --- | --- | --- |
| Milvus | banco vetorial | container `vetores`, porta `${INDICE_PORTA_MILVUS}` (19530) |
| Ollama | gera embeddings (modelo pequeno, sem LLM) | container `embeddings`, porta `${INDICE_PORTA_OLLAMA}` (11434) |
| `@zilliz/claude-context-mcp` | o servidor que INDEXA — o `indexar.py` fala com ele por JSON-RPC; como cliente MCP da sessão, só onde a política deixar | instalado fora do repositório (seção "Quando o ambiente é trancado") |
| `buscar.py` | a porta de busca da sessão: HTTP puro, busca híbrida, biblioteca padrão | `.agents/indice/buscar.py` |

**A porta normal para o acervo é o `buscar.py`, não o cliente MCP.** Medido em
02/09/2026: a política de uma organização passou a barrar todo servidor MCP
fora de uma lista fechada, e os servidores sumiram da sessão sem aviso — o
índice continuou de pé, mas inalcançável. O buscador fala HTTP com o banco e
com o gerador de vetores, usa só a biblioteca padrão do Python e faz a mesma
busca híbrida que o MCP fazia. Onde a política deixar, o MCP segue funcionando
ao lado; não há nada a desfazer.

**O banco é sempre derivado. Nada nasce dentro dele.** Se os volumes sumirem,
reindexar reconstrói tudo do código-fonte. Por isso os volumes são nomeados e
locais — nenhum dado do índice entra em git nenhum.

## Subir, e registrar o MCP onde a política deixar

```bash
docker compose -f .agents/indice/docker-compose.yml -p indice up -d
docker exec indice-embeddings-1 ollama pull nomic-embed-text
```

O registro abaixo é opcional: ele dá à sessão a ferramenta `search_code` do
MCP. Sem ele, ou onde a política o barrar, a busca é pelo `buscar.py` e nada
mais muda.

```bash
claude mcp add indice \
  -e EMBEDDING_PROVIDER=Ollama \
  -e EMBEDDING_MODEL=nomic-embed-text \
  -e OLLAMA_HOST=http://127.0.0.1:11434 \
  -e MILVUS_ADDRESS=127.0.0.1:19530 \
  -- npx @zilliz/claude-context-mcp@0.1.15
```

A versão do servidor MCP vai presa, nunca `@latest`: o `npx` baixa a versão
que estiver publicada a cada abertura de sessão, e uma versão nova que mude o
formato do índice derruba a busca calada. Para subir de versão, troque o
número aqui, remova e registre de novo (`claude mcp remove indice` antes do
`add`), e reindexe se a nota de versão pedir. Medido em 02/09/2026: a versão
publicada era a 0.1.15.

As portas saem de `${INDICE_PORTA_MILVUS}`, `${INDICE_PORTA_SAUDE}` e
`${INDICE_PORTA_OLLAMA}` se as padrão estiverem ocupadas. As ferramentas que o
MCP expõe: `index_codebase`, `search_code`, `get_indexing_status`,
`clear_index`.

## Quando o ambiente é trancado

Ambiente corporativo com proxy que reassina TLS e política de pacote costuma
recusar quatro coisas desta receita. **A premissa "tudo local" continua de
pé** — Milvus e Ollama sobem, o modelo gera vetores, nada sai da máquina. O
que não se sustenta é a INSTALAÇÃO pela via padrão.

Cada trava abaixo traz o contorno e diz se ele foi **provado** ou se é
**relato de campo ainda não reexecutado**. Não invente um quinto caminho: o
que travar fora desta lista é achado para o dono, com a mensagem de erro
exata, não conserto seu.

### 1. O `npm` não instala a dependência nativa — PROVADO

`faiss-node` baixa binário de fora na instalação e falha atrás de proxy
autenticado. A saída é não rodar os scripts de instalação:

**Instale FORA do repositório.** São ~400 MB e três arquivos, e dois deles
o git não ignora — rodar na raiz do projeto suja o repositório de quem
instalou:

```bash
mkdir -p ~/atlas-indice && cd ~/atlas-indice
npm install --ignore-scripts @zilliz/claude-context-mcp@0.1.15
```

**Prove antes de registrar o servidor.** Instalar não é funcionar, e sem as
variáveis o servidor tenta OpenAI e morre por motivo ERRADO — quem vir esse
erro vai culpar a instalação:

```bash
cd ~/atlas-indice
export EMBEDDING_PROVIDER=Ollama EMBEDDING_MODEL=nomic-embed-text
export OLLAMA_HOST=http://127.0.0.1:11434 MILVUS_ADDRESS=127.0.0.1:19530
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"sonda","version":"1"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
| timeout 25 node node_modules/@zilliz/claude-context-mcp/dist/index.js 2>&1 \
| grep -oE 'index_codebase|search_code|clear_index|get_indexing_status|Cannot find module' | sort -u
```

Tem de sair exatamente isto, e nada mais:

```
clear_index
get_indexing_status
index_codebase
search_code
```

**Se sair `Cannot find module`, é dependência de par que não veio.** O
`--ignore-scripts` não impede peer, mas a instalação automática de peer
depende da versão do `npm` — e a receita não pode depender de comportamento
que ela não declara. Medido: com npm 11 o `@langchain/core` veio junto; num
ambiente com npm mais antigo, não veio, e o servidor não subiu. A saída é
instalar o que faltar, pela mesma via:

```bash
npm install --ignore-scripts "@langchain/core@0.3"
```

E sondar de novo. Só registre o servidor depois que a sonda listar as
quatro.

**Por que pular os scripts não perde nada, medido:** o `dist` do pacote não
referencia `faiss` em lugar nenhum e `dist/vectordb/` só traz Milvus — ou
seja, `faiss` é peso morto declarado nas dependências. E o `tree-sitter`, que
também é nativo mas este É usado pelo cortador por AST, traz binário pronto
DENTRO do pacote (`tree-sitter/prebuilds/<plataforma>/`), então não depende
de download.

Provado ponta a ponta: a instalação sem scripts completa, o binário nasce em
`node_modules/.bin/claude-context-mcp`, o servidor sobe e lê as variáveis, a
indexação roda, o corte por AST engata (os pedaços são trechos dentro do
arquivo, não o arquivo inteiro) e a busca por significado responde.

**Ressalva medida:** a qualidade da busca varia com o ACERVO, não com o modo
de instalação. Num corpo de arquivos parecidos entre si, pergunta com
vocabulário distintivo acha o alvo nas primeiras posições e pergunta genérica
erra. Isso vale para qualquer instalação.

### 2. O registro de modelo é bloqueado — RELATO DE CAMPO

`ollama pull` busca num registro que a política de URL pode barrar por
categoria. O contorno é trazer o arquivo do modelo por outra via já liberada
e importá-lo:

```bash
docker cp <modelo>.gguf indice-embeddings-1:/tmp/modelo.gguf
docker exec indice-embeddings-1 sh -c \
  'printf "FROM /tmp/modelo.gguf\n" > /tmp/Modelfile \
   && ollama create nomic-embed-text -f /tmp/Modelfile'
```

O modelo tem de ser o mesmo (`nomic-embed-text`, ~274 MB, 768 dimensões):
trocar de modelo muda a dimensão do vetor e invalida o índice inteiro.

### 3. Os contêineres não confiam na autoridade do proxy — RELATO DE CAMPO

O proxy reassina o TLS com autoridade interna, e o contêiner não a conhece:
o erro é `x509: certificate signed by unknown authority`. O contorno é montar
a autoridade em PEM e apontá-la, num arquivo à parte que não se versiona:

```yaml
# .agents/indice/docker-compose.override.yml — local, fora do git
services:
  embeddings:
    volumes:
      - ${CAMINHO_DA_CA_INTERNA}:/etc/ssl/certs/ca-interna.pem:ro
    environment:
      SSL_CERT_FILE: /etc/ssl/certs/ca-interna.pem
```

O caminho da autoridade vai por variável, nunca escrito no arquivo: caminho
de máquina não entra em texto rastreado.

### 4. O `claude mcp add` é barrado por política — RELATO DE CAMPO

A política de empresa pode barrar o comando do CLI **sem barrar o servidor**.
Registrar direto no `.mcp.json` do repositório funciona, e por isso ele é o
método primário onde o CLI não passa:

```json
{
  "mcpServers": {
    "indice": {
      "command": "node",
      "args": ["node_modules/@zilliz/claude-context-mcp/dist/index.js"],
      "env": {
        "EMBEDDING_PROVIDER": "Ollama",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "OLLAMA_HOST": "http://127.0.0.1:11434",
        "MILVUS_ADDRESS": "127.0.0.1:19530"
      }
    }
  }
}
```

Com a instalação do item 1, o `command` é `node` apontando para o arquivo
instalado — não `npx`, que voltaria a buscar o pacote na rede a cada abertura
de sessão.

## O que este módulo não é

- Não é LLM local: o Ollama aqui só transforma texto em vetor
  (`nomic-embed-text`, ~274 MB). Inferência local foi medida e descartada no
  workspace de origem.
- Não é LLM nem memória de sessão: a memória mora em arquivos `.md`. O que
  o índice faz por ela é a busca por sentido — o mesmo `index_codebase`
  aceita a pasta da memória e as pastas de conhecimento do workspace, porque
  `.md` está entre as extensões padrão. Um índice de texto à parte foi medido
  e descartado: peça caseira que ninguém manteve.
- Não indexa por padrão: cada máquina decide o que indexar, e o índice nunca
  viaja — só a receita.

## Indexar em segundo plano, sem depender da sessão

Indexar o acervo inteiro leva horas — 18 arquivos levaram cerca de um minuto e
meio, e um workspace de milhares de arquivos escala daí. Por isso existe o
`indexar.py`, que fala JSON-RPC **direto com o servidor**, sem passar pelo
cliente MCP da sessão: assim a indexação sobrevive à sessão que a disparou, e
pode rodar de madrugada.

Ele lê `.agents/indice/alvos.json`, que é **local** — caminho de máquina não
entra em git:

```json
{
  "servidor": "~/.local/share/atlas-indice/node_modules/@zilliz/claude-context-mcp/dist/index.js",
  "ambiente": {
    "EMBEDDING_PROVIDER": "Ollama",
    "EMBEDDING_MODEL": "nomic-embed-text",
    "OLLAMA_HOST": "http://127.0.0.1:11434",
    "MILVUS_ADDRESS": "127.0.0.1:19530"
  },
  "alvos": ["conhecimento", ".agents/skills", "projetos/algum-repositorio"],
  "ignorar": ["**/.docusaurus/**", "**/build/**", "**/node_modules/**"]
}
```

**Rode o ensaio ANTES da rodada real, e olhe as colunas.** Ele conta os
arquivos sob cada alvo, quantos deles o git rastreia e quantos têm extensão
que o servidor instalado indexa — essa última lista ele lê do código do
próprio servidor, não de uma cópia:

```
ENSAIO — 2 alvo(s), nada será indexado:
  conhecimento — 4972 arquivo(s) sob ele, 277 rastreado(s) no git, 260 com extensão que o servidor indexa
      ATENÇÃO: 4695 arquivo(s) que o git não rastreia — quase sempre
      artefato de build ou cache. Indexá-los é lento e enche o índice de
      lixo. Declare `ignorar` em .agents/indice/alvos.json
```

Foi assim que um acervo real se revelou: 4.972 arquivos no disco contra 277
versionados — o resto era saída de build de um site de documentação.

**Mas leia o aviso com cuidado antes de agir:** o servidor filtra por
extensão, então imagem e binário **não entram no índice** — medido aqui, 17
arquivos no disco viraram 14 indexados. O que o excesso custa de fato é a
varredura da árvore; o índice só se enche de lixo se o excesso for texto ou
código. Confira de onde vem antes de decidir. O `ignorar` vira
`ignorePatterns` na chamada.

```bash
python3 .agents/indice/indexar.py --ensaio      # mostra os alvos e o tamanho
python3 .agents/indice/indexar.py               # indexa, esperando cada um terminar
python3 .agents/indice/indexar.py --refazer     # reindexa o que já está indexado
```

**Por que ele ESPERA, e por que isso não é detalhe:** o `index_codebase`
devolve na hora e indexa em segundo plano. Quem dispara e encerra o processo
**aborta o trabalho do servidor** — a rodada parece ter terminado em zero
segundo e o índice fica pela metade. O instrumento consulta o estado até o
servidor dizer `Status: completed`.

E ele separa três vereditos, porque os três significam coisas diferentes:
**indexado** (terminou agora), **já estava indexado** (não é falha; use
`--refazer` se quiser) e **FALHOU**, com o texto do servidor colado. A marca
de "já indexado" chega com `isError` DENTRO do resultado, então olhar só o
erro de topo transforma recusa em sucesso.

## O que o servidor pula — lido no código dele, e reproduzido

O servidor indexa menos do que parece, e não avisa. As quatro causas abaixo
foram lidas no código da versão instalada e reproduzidas em pastas de
controle; o ensaio acusa cada uma **antes** de você disparar, com a saída.

1. **`.json` não está na lista de extensões.** A lista padrão tem 25
   extensões, e `.json`, `.yaml`, `.txt`, `.html` e `.sql` estão **comentadas**
   no código. Reproduzido: pasta só com um JSON de 19 KB não indexa nada;
   a mesma pasta com um `.md` ao lado indexa 1 arquivo em 14 s. Não é
   densidade — é filtro. Onde o mesmo conteúdo existe em prosa (uma página
   gerada a partir do JSON), aponte o alvo para a prosa.
2. **Alvo sem arquivo elegível nunca termina.** O servidor acha 0 arquivos,
   marca 100% e se recusa a gravar o estado "completed" com zero — então
   `get_indexing_status` diz "indexando" para sempre, e quem espera o fim
   espera o teto inteiro. Foi isso que pareceu "30 minutos e zero gravado".
   O indexador agora **pula** esse alvo em vez de esperar.
3. **Pasta que começa com ponto é pulada em qualquer profundidade.**
   `.claude/`, `.agents/`, `.github/` nunca entram quando o alvo é a raiz —
   para indexá-las, declare cada uma como alvo próprio (é por isso que
   `.agents/skills` é um alvo, não parte de outro).
4. **`!pasta/` no `.gitignore` não reabre a pasta.** O servidor lê os
   `.*ignore` da raiz do alvo e respeita as exceções, mas testa o nome da
   pasta **sem** a barra antes de testar com ela: a exclusão anterior (`*`)
   vence, e a pasta reaberta fica de fora. Medido num alvo real: 4 páginas
   sob uma pasta reaberta por `!prompts/` não entraram; com `!prompts`, sem a
   barra — que o git aceita igual —, entraram. O ensaio acusa a linha exata.

```
  nucleo — 6 arquivo(s) sob ele, 5 rastreado(s) no git, 0 com extensão que o servidor indexa
      ATENÇÃO: nenhum arquivo com extensão que o servidor aceite. Ele acha 0, marca 100% e NUNCA diz completed (...)
      ATENÇÃO: 6 arquivo(s) .json — a extensão .json NÃO está na lista do servidor instalado (...)
```

A contagem de elegíveis é a que se compara com o que o servidor diz ter
indexado no fim de cada alvo: divergência ali tem uma dessas quatro causas, e
o ensaio diz qual.

## Buscar — a porta normal

```bash
python3 .agents/indice/buscar.py "o que fazer quando a cópia diverge da fonte"
python3 .agents/indice/buscar.py "vetar-andamento-em-arquivo" --alvo skills --quantos 3
python3 .agents/indice/buscar.py "..." --denso      # só significado, para comparar
python3 .agents/indice/buscar.py --medir            # denso contra híbrido, no seu acervo
```

**Ele descobre sozinho o que está indexado.** O servidor grava o caminho de
cada acervo na descrição da coleção, e o buscador lê isso do banco: nenhuma
lista local de alvos a manter. `--alvo` restringe a um caminho, pelo fim dele
ou pelo caminho absoluto; alvo que não está no banco é recusado com a lista do
que existe, nunca devolvido como vazio. O `alvos.json` só entra pelos
endereços dos serviços, e sem ele valem os padrões locais.

**A busca é híbrida, e isso é medido, não gosto.** Cada pergunta corre em duas
pernas na mesma coleção — o vetor denso, que acha por significado, e o BM25 no
campo esparso, que acha por termo exato — e o banco funde as duas por RRF.
Denso puro perde justamente onde a sessão mais precisa: nome de gancho, nome
de função, palavra rara. A medição é reprodutível e mora no instrumento:
`--medir` tira do próprio acervo perguntas por termo único com resposta
conhecida (arquivo:linha), roda cada uma nos dois modos, repete para medir o
ruído e exige que o híbrido vença ou empate no topo e nos três primeiros — o
`--testar` falha se não vencer. Medido em 02/09/2026 num acervo de 9 coleções,
59 perguntas: o híbrido acertou o topo em 34 contra 13 do denso, e os três
primeiros em 48 contra 22, com ruído zero em 236 chamadas. Em dez perguntas em
linguagem natural, escritas à mão, o híbrido acertou o topo em 6 contra 3 — e
perdeu uma: a fusão não é ganho em toda pergunta, é ganho no total.

**O que ele devolve, e o que a pontuação significa:**

```
BUSCA híbrida (significado + termo exato) — "regenere a cópia e prove antes de entregar" em 1 alvo(s)
  <raiz>/conhecimento
    [0.020] regras-da-camada.md:218
           15. **Editou a fonte, regenere a cópia e prove — antes de entregar.** ...
```

A pontuação é a semelhança medida, **não a certeza**: o banco sempre devolve
os mais próximos que tiver, mesmo quando nenhum serve. Leia o trecho antes de
confiar nele. Na busca híbrida a pontuação é a do RRF (pequena, por
construção); na densa é a semelhança de cosseno.

**Como alvo vira coleção, medido:** o nome é `hybrid_code_chunks_` mais os
oito primeiros dígitos do md5 do caminho **absoluto**. Cada caminho indexado é
uma coleção própria — buscar em coleção alheia devolve o melhor resultado
*dela*, que costuma não ter nada a ver com a pergunta.

## Indexar conhecimento, não só código

O mesmo índice cobre o que a sessão lê antes de agir — a memória e as
páginas de conhecimento —, e é aí que ele mais poupa contexto: a sessão
pergunta "o que já se decidiu sobre X" em vez de abrir arquivo por arquivo.
Aponte `index_codebase` para cada pasta, uma por vez; pasta de credencial ou
de rascunho confidencial fica fora, mesmo o índice sendo local.

```
index_codebase  ${HOME}/.claude/projects/<raiz-com-hifens>/memory
index_codebase  <raiz>/conhecimento
index_codebase  <workspace-privado>/conhecimento
```

Reindexar é barato: só o que mudou volta ao banco (árvore de Merkle).

## Prova de saúde

```bash
curl -sf localhost:${INDICE_PORTA_SAUDE:-9091}/healthz && echo vetores ok
curl -sf localhost:${INDICE_PORTA_OLLAMA:-11434}/api/tags | grep -q nomic && echo embeddings ok
```

Os serviços declaram `restart: unless-stopped`: quando o daemon do Docker
sobe junto com a máquina, os containers voltam sozinhos depois da
reinicialização. Quem os quer parados usa `docker compose down` — parado por
ordem fica parado. `down` sem `-v` preserva os volumes: o índice sobrevive.
`down -v` apaga — e reindexar reconstrói, porque o banco é derivado.
