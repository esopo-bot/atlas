# indice

Busca no acervo pelo `ck` no modo léxico: termo e palavra, ranqueados por
BM25, com o índice em arquivo dentro de cada alvo — sem serviço de pé e sem
modelo baixado. Sem o `ck` no PATH, a busca cai no grep e avisa.

```bash
python <pasta do clone do atlas>/montar.py --modulo indice
python .agents/indice/indexar.py --estado
```

O índice não tem servidor MCP: o do ck expõe três ferramentas que baixam
modelo e não se desligam, e a porta é o `buscar.py`.

A receita inteira — instalar o ck, o que ele grava em cada alvo, indexar,
buscar e o que acontece sem ele — está na página `conhecimento/indice.md`,
que viaja junto.
