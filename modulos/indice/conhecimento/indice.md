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
  -- npx @zilliz/claude-context-mcp@latest
```

As portas saem de `${INDICE_PORTA_MILVUS}`, `${INDICE_PORTA_SAUDE}` e
`${INDICE_PORTA_OLLAMA}` se as padrão estiverem ocupadas. As ferramentas que o
MCP expõe: `index_codebase`, `search_code`, `get_indexing_status`,
`clear_index`.

## O que este módulo não é

- Não é LLM local: o Ollama aqui só transforma texto em vetor
  (`nomic-embed-text`, ~274 MB). Inferência local foi medida e descartada no
  workspace de origem.
- Não é memória: a memória de sessão mora em arquivos `.md` e se busca com
  instrumento próprio de FTS5 — banco vetorial perdeu esse teste em 5 de 5
  perguntas.
- Não indexa por padrão: cada máquina decide o que indexar, e o índice nunca
  viaja — só a receita.

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
