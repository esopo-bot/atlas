# indice

Busca por significado no código dos repositórios do workspace — a sessão
pergunta em linguagem natural e recebe o trecho, em vez de varrer com `grep`
até acertar a palavra. Vale a pena a partir de milhares de arquivos; abaixo
disso o `grep` ganha, e a página do módulo traz a régua medida.

Duas peças de terceiros, nenhuma escrita aqui: o banco vetorial (Milvus, em
container) e o gerador de embeddings (Ollama, em container, modelo pequeno —
nada de LLM local). Quem indexa é o servidor `@zilliz/claude-context-mcp`,
conduzido pelo `indexar.py`; quem busca é o `buscar.py`, por HTTP puro — a
porta normal, porque política de organização pode barrar todo MCP sem aviso.

```bash
python montar.py --modulo indice
docker compose -f .agents/indice/docker-compose.yml -p indice up -d
docker exec indice-embeddings-1 ollama pull nomic-embed-text
```

**O banco é sempre derivado.** Nada nasce dentro dele: apagar os volumes e
reindexar reconstrói tudo. A receita inteira — subir, indexar, buscar, e o registro
do MCP, que o `montar.py --atualizar` faz sozinho no `.mcp.json` — está na página
`conhecimento/indice.md`, que viaja junto.

**Ambiente corporativo trancado recusa as três linhas acima.** Proxy que
reassina TLS, registro de pacote bloqueado por política e CLI barrado por
regra de empresa têm contorno — os quatro estão na seção "Quando o ambiente
é trancado" da mesma página. Não invente um quinto: o que travar fora da
lista é achado para o dono, com a mensagem de erro exata.
