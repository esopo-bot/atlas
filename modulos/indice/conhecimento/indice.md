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
| `@zilliz/claude-context-mcp` | o servidor MCP que a sessão usa | `npx`, registrado por `claude mcp add` |

**O banco é sempre derivado. Nada nasce dentro dele.** Se os volumes sumirem,
reindexar reconstrói tudo do código-fonte. Por isso os volumes são nomeados e
locais — nenhum dado do índice entra em git nenhum.

## Subir e registrar

```bash
docker compose -f .agents/indice/docker-compose.yml -p indice up -d
docker exec indice-embeddings-1 ollama pull nomic-embed-text
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

```bash
npm install --ignore-scripts @zilliz/claude-context-mcp@0.1.15
node node_modules/@zilliz/claude-context-mcp/dist/index.js
```

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
  "alvos": ["conhecimento", ".agents/skills", "projetos/algum-repositorio"]
}
```

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
