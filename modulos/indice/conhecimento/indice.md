# O índice de código

Busca por significado no código dos repositórios: a sessão pergunta "onde a
autenticação decide quem entra" e recebe o trecho, sem depender de acertar a
palavra que o autor usou. Chega pelo módulo `indice`
(`python <pasta do clone do atlas>/montar.py --modulo indice`, rodado de
dentro do repositório que o recebe).

## Quando ele vale a pena — a régua medida

Abaixo de ~2 mil arquivos rastreados o `grep` ganha; acima de ~10 mil o
índice ganha claro; no meio, decide a dor de varrer o mesmo repositório
várias vezes por pergunta. Conte antes: `git ls-files | wc -l`.

## As peças

| Peça | O quê | Onde |
| --- | --- | --- |
| Milvus | banco vetorial | container `vetores`, porta `${INDICE_PORTA_MILVUS}` (19530) |
| Ollama | gera embeddings (modelo pequeno, sem LLM) | container `embeddings`, porta `${INDICE_PORTA_OLLAMA}` (11434) |
| `@zilliz/claude-context-mcp` | o servidor que indexa; o `indexar.py` fala com ele por JSON-RPC | instalado fora do repositório |
| `buscar.py` | a porta de busca da sessão: HTTP puro, busca híbrida, biblioteca padrão | `.agents/indice/buscar.py` |
| `subir.py` | sobe as duas peças e liga a placa de vídeo quando o docker a entrega | `.agents/indice/subir.py` |

A porta normal para o acervo é o `buscar.py`, não o cliente MCP: política
de organização pode barrar servidor MCP sem aviso, e o buscador segue de pé.
O banco é derivado: sumiu o volume, reindexa. Nada do índice entra em git.

## Subir e registrar

```bash
python .agents/indice/subir.py            # sobe, baixa o modelo, liga a placa se houver
python .agents/indice/subir.py --ensaio   # mostra a decisão sem subir
python .agents/indice/subir.py --saude    # sonda as duas peças e o modelo; sai 1 nomeando o que falta
```

Quem já tinha o módulo roda `montar.py --modulo indice` de novo para receber
peça nova: o `--sincronizar` só regrava cópia que já está em uso. A placa
medida na mesma máquina rende 7,2 vezes a CPU (232 contra 32 pedaços por
minuto); o instrumento a liga só se ela aparecer dentro de um contêiner de
verdade. Comandos crus, com o arquivo da placa como `-f` a mais (o `-f`
explícito não carrega o `docker-compose.override.yml` sozinho):

```bash
docker compose -f .agents/indice/docker-compose.yml \
               -f .agents/indice/docker-compose.gpu.yml -p indice up -d
docker exec indice-embeddings-1 ollama pull nomic-embed-text
```

Quem registra o servidor MCP é `montar.py --atualizar`: escreve `indice` no
`.mcp.json` da raiz (no Windows por `cmd /c npx`), entra uma linha por
servidor em `allowedMcpServers` do `.claude/settings.local.json` (a lista
branda de organização some com servidor local sem isso) e espelha o
`mcpServers` em `.devin/mcp_config.local.json`. À mão:

```bash
claude mcp add indice \
  -e EMBEDDING_PROVIDER=Ollama -e EMBEDDING_MODEL=nomic-embed-text \
  -e OLLAMA_HOST=http://127.0.0.1:11434 -e MILVUS_ADDRESS=127.0.0.1:19530 \
  -- npx @zilliz/claude-context-mcp@0.1.15
```

Versão presa, nunca `@latest`: versão nova que mude o formato do índice
derruba a busca calada. Para subir, `claude mcp remove indice`, `add` com o
número novo, e reindexe se a nota pedir. Ferramentas do MCP:
`index_codebase`, `search_code`, `get_indexing_status`, `clear_index`.

## Quando o ambiente é trancado

A premissa "tudo local" continua; o que trava é a instalação pela via
padrão. O que travar fora desta lista é achado para o dono, com a mensagem
exata, não conserto seu.

| Trava | Contorno | Estado |
| --- | --- | --- |
| `npm` não instala a dependência nativa (`faiss-node` baixa binário atrás do proxy) | `npm install --ignore-scripts @zilliz/claude-context-mcp@0.1.15` numa pasta FORA do repositório (~400 MB); `faiss` é peso morto e o `tree-sitter` traz binário pronto; se a sonda abaixo disser `Cannot find module`, `npm install --ignore-scripts "@langchain/core@0.3"` | provado |
| registro de modelo bloqueado (`ollama pull`) | traga o `.gguf` por via liberada, `docker cp` para o contêiner e `ollama create nomic-embed-text -f Modelfile`; mesmo modelo (768 dimensões), senão o índice inteiro invalida | relato de campo |
| contêiner não confia na autoridade do proxy (`x509: unknown authority`) | `docker-compose.override.yml` local, fora do git, montando `${CAMINHO_DA_CA_INTERNA}` em `/etc/ssl/certs/ca-interna.pem` e `SSL_CERT_FILE` apontando para ele | relato de campo |
| `claude mcp add` barrado por política | registre direto no `.mcp.json`, com `command: node` apontando para o `dist/index.js` instalado e o `env` das quatro variáveis | relato de campo |
| servidor declarado some da sessão | lista branda `allowedMcpServers` gerenciada: o `--atualizar` gera a entrada exata; com `allowManagedMcpServersOnly` ligado só o administrador inclui, e o `buscar.py` segue | provado |

Prove antes de registrar (sem as variáveis o servidor tenta OpenAI e morre
por motivo errado):

```bash
export EMBEDDING_PROVIDER=Ollama EMBEDDING_MODEL=nomic-embed-text
export OLLAMA_HOST=http://127.0.0.1:11434 MILVUS_ADDRESS=127.0.0.1:19530
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"sonda","version":"1"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
| timeout 25 node node_modules/@zilliz/claude-context-mcp/dist/index.js 2>&1 \
| grep -oE 'index_codebase|search_code|clear_index|get_indexing_status|Cannot find module' | sort -u
```

Tem de sair as quatro ferramentas, e nada mais.

## Indexar em segundo plano

O `indexar.py` fala JSON-RPC direto com o servidor: a indexação sobrevive à
sessão e pode rodar de madrugada. Ele lê `.agents/indice/alvos.json`, que
é local:

```json
{
  "servidor": "~/.local/share/atlas-indice/node_modules/@zilliz/claude-context-mcp/dist/index.js",
  "ambiente": {
    "EMBEDDING_PROVIDER": "Ollama",
    "EMBEDDING_MODEL": "nomic-embed-text",
    "OLLAMA_HOST": "http://127.0.0.1:11434",
    "MILVUS_ADDRESS": "127.0.0.1:19530",
    "EMBEDDING_BATCH_SIZE": "10"
  },
  "alvos": ["conhecimento", ".agents/skills", "projetos/algum-repositorio"],
  "ignorar": ["**/.docusaurus/**", "**/build/**", "**/node_modules/**"]
}
```

`EMBEDDING_BATCH_SIZE` é obrigatório em CPU: lote de 100 estoura os 5 min do
`fetch` do Node e a coleção fica pela metade.

```bash
python .agents/indice/indexar.py --ensaio      # conta arquivos, rastreados e elegíveis por alvo
python .agents/indice/indexar.py               # indexa, um alvo por vez, esperando cada um
python .agents/indice/indexar.py --refazer     # reindexa o que já está indexado
python .agents/indice/indexar.py --ligar       # a rotina indice do ritual passa a rodar --ronda
python .agents/indice/indexar.py --estado      # como está, a última ronda e coleções sem alvo
```

Leia o ensaio antes da rodada real: alvo com milhares de arquivos fora do
git é saída de build, e vai para `ignorar`. O que o servidor pula, lido no
código dele e reproduzido: `.json`, `.yaml`, `.txt`, `.html` e `.sql` estão
fora da lista de extensões; alvo sem arquivo elegível nunca diz `completed`
(o indexador o pula); pasta que começa com ponto é pulada em qualquer
profundidade (declare `.agents/skills` como alvo próprio); `!pasta/` no
`.gitignore` não reabre a pasta, `!pasta` sem barra reabre.

Por que ele espera e indexa um alvo por vez: `index_codebase` devolve na
hora e indexa de fundo, e a consulta de estado grava como `completed`
qualquer alvo com linhas no banco, inclusive o que está em curso. O
indexador espera pela marca no stderr do servidor que nomeia o alvo, empurra
a sincronização periódica para 24 h, e dá `clear_index` no alvo que estourou
o teto ou falhou. Servidor MCP órfão (o `npx` do `.mcp.json` que a sessão
deixou vivo) sincroniza a cada 5 min por fora e deixa a trava
`~/.context/mcp-sync.lock`: a ronda remove a trava de processo morto.

## Buscar

```bash
python .agents/indice/buscar.py "o que fazer quando a cópia diverge da fonte"
python .agents/indice/buscar.py "vetar-andamento-em-arquivo" --alvo skills --quantos 3
python .agents/indice/buscar.py "..." --teto-total 60   # teto da resposta inteira, em trechos
python .agents/indice/buscar.py "..." --denso           # só significado, para comparar
python .agents/indice/buscar.py --medir                 # denso contra híbrido, no seu acervo
```

O buscador lê do banco o que está indexado; `--alvo` restringe pelo fim do
caminho ou pelo caminho absoluto, e alvo fora do banco é recusado com a
lista. A resposta diz quando cortou no teto. A busca é híbrida (vetor denso
mais BM25, fundidos por RRF) porque denso puro perde nome de gancho, de
função e palavra rara; o `--medir` prova isso no seu acervo e o `--testar`
falha se o híbrido não vencer. A pontuação é semelhança, não certeza: leia o
trecho. Cada caminho indexado é uma coleção `hybrid_code_chunks_` mais os
oito primeiros dígitos do md5 do caminho absoluto.

O mesmo índice cobre a memória e as páginas de conhecimento: aponte um
alvo por pasta; credencial e rascunho confidencial ficam fora.
