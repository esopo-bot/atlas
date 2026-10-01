# O índice do acervo

O índice é o `ck` no modo léxico: acha por termo e palavra, ranqueados por
BM25, com o índice em arquivo dentro de cada alvo. Nenhum serviço fica de pé
e nenhum modelo é baixado. Sem o `ck` no PATH, a busca cai no grep e avisa.

O léxico acha palavra, não sinônimo: pergunte com as palavras que o texto
usa. A medição que decidiu a troca, contra o motor antigo, está na issue 514.

## Instalar o ck

1. Baixe o zip da sua plataforma nas versões de `github.com/BeaconBay/ck`,
   confira o SHA-256 publicado e ponha o `ck` numa pasta do PATH. Quem tem
   Rust pode usar `cargo install ck-search`.
2. Prove com `ck --version` e com `python .agents/indice/indexar.py
   --estado`, que diz a linha `motor: ck ... modo léxico`.

**Só o modo léxico.** O instrumento chama `ck --lex` e nada mais. Os modos
`--sem`, `--hybrid`, `--index`, `--rerank` e `--switch-model` baixam modelo
de embedding para a pasta de modelos do ck: `$XDG_CACHE_HOME/ck/models`,
senão `~/.cache/ck/models`, senão `%LOCALAPPDATA%/ck/cache/models`. Pasta
que não existe é a prova de que nada foi baixado.

## O que o ck grava em cada alvo

O ck grava `.ck/` na pasta que indexa e, às vezes, um `.ckignore`. Subpasta
de um alvo já indexado usa o índice de cima, e não nasce outro. O índice é
derivado: apagar `.ck/` e rodar a ronda o reconstrói.

| o alvo | como o git não vê o `.ck/` |
| --- | --- |
| o repositório onde a camada mora | `.gitignore`, com `.ck/` e `.ckignore`; o `montar.py` leva as duas linhas para quem instala |
| um vizinho com git | o `.git/info/exclude` dele, que é local; o instrumento acrescenta as duas linhas antes do primeiro índice, e o `.gitignore` rastreado do vizinho não muda |
| uma pasta sem git | nada a esconder |

## Indexar

```bash
python .agents/indice/indexar.py --ensaio    # o que cada alvo recebe, sem indexar
python .agents/indice/indexar.py             # indexa os alvos declarados
python .agents/indice/indexar.py --refazer   # apaga o índice de cada alvo e refaz
python .agents/indice/indexar.py --ligar     # o ritual passa a rodar a ronda
python .agents/indice/indexar.py --estado    # ligado, o ck e a última ronda
```

Os alvos moram em `.agents/indice/alvos.json`, arquivo local:

- `alvos`: os caminhos; relativo é da raiz principal do repositório.
- `ligado`: a ronda só roda ligada.
- `ignorar`: cada padrão vira `--exclude` do ck, pelo nome da pasta.

Os campos `servidor` e `ambiente` do motor antigo não são mais lidos.

A ronda (`--ronda`) é a rotina `indice` do ritual. Ela diz, por alvo,
indexado, atualizado ou já estava. Quando nada mudou, compara o tempo com a
meta que o instrumento declara e imprime, e reprova acima dela. A última
ronda fica em `.agents/indice/ultima-ronda.json`.

## Buscar

```bash
python .agents/indice/buscar.py "<termo ou palavras>" --alvo <fim do caminho> --quantos 3
python .agents/indice/buscar.py "..." --teto-total 60   # teto da resposta inteira
```

A saída traz, por alvo, `[pontos] arquivo:linha` e o trecho. O `--alvo`
casa pelo caminho de um alvo declarado, pelo fim dele, ou por uma pasta que
exista, que o ck indexa na primeira busca. `--denso` e `--medir` seguem
aceitos, mas o motor léxico não tem modo denso para comparar.

## Sem o ck

- `buscar.py` avisa numa linha e cai no grep: `git grep` onde há git, senão
  uma varredura em Python. A saída é a mesma; os pontos são a fração das
  palavras da pergunta que a linha tem.
- `indexar.py --estado` diz que o ck falta e como instalar; a ronda ligada
  reprova.
- A abertura, `python .agents/camada/camada.py --abertura`, e o aviso de
  início de sessão acusam só isso.

## Sem servidor de contexto

O índice não tem servidor MCP, porque o do ck expõe `semantic_search`,
`hybrid_search` e `reindex`, que baixam modelo na primeira chamada e não se
desligam; a porta é o `buscar.py`.

## O motor antigo

O banco de vetores com o gerador de embeddings ficou desligado, não
apagado: `subir.py` e os `docker-compose*.yml` seguem em `.agents/indice/`,
e nem o `buscar.py` nem o `indexar.py` falam mais com eles.
