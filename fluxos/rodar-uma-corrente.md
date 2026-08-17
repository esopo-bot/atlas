# Rodar uma corrente

O passo a passo do motor opcional: uma corrente de etapas, um recibo por
etapa, do módulo `encadeador`. Quem só usa as skills não precisa desta
página.

## Antes de tudo — uma vez por casa

```bash
python montar.py --modulo encadeador
python .agents/recibo/recibo.py --testar
python .agents/conferir/conferir.py --testar
python .agents/encadeador/encadeador.py --testar
```

O módulo exige a camada no destino — ele usa `recibo.py` e `conferir.py`
como estão. Os três `--testar` são o primeiro comando de qualquer retomada:
se algum falhar, nada do resto vale.

## 1 · O manifesto

Um JSON com as etapas, as dependências e o teto de ciclos:

```json
{
  "teto": 3,
  "ambiente": {"venv": ".venv", "env": ".credenciais/mcp.env"},
  "etapas": [
    {"nome": "prepara", "tipo": "codigo", "comando": "bash prepara.sh"},
    {"nome": "analisa", "tipo": "sessao", "prompt": "o pedido, completo",
     "depende": ["prepara"]},
    {"nome": "confere", "tipo": "conferencia", "depende": ["analisa"]},
    {"nome": "aprova", "tipo": "portao",
     "aprovacao": "aprovacoes/pr.ok", "depende": ["confere"]}
  ]
}
```

Quatro tipos de etapa:

| Tipo | O que faz |
| --- | --- |
| `codigo` | roda um comando; o stdout tem de ser um recibo válido |
| `sessao` | roda `claude -p` com o prompt — as regras da camada e a `configuracao-da-casa.md` entram na frente, por código |
| `conferencia` | re-executa o `provado` dos recibos desta execução e acusa divergência |
| `portao` | espera o arquivo de aprovação do dono — a corrente não decide por ele |

Etapas sem dependência entre si rodam juntas (fork); `conferencia` e
`portao` nunca dividem onda com ninguém.

## 2 · O ensaio — sempre antes

```bash
python .agents/encadeador/encadeador.py ensaio --manifesto corrente.json --trabalho meu-trabalho
```

Lista as ondas inteiras sem executar **nada** — nem comando, nem sessão,
nem leitura do arquivo de ambiente.

## 3 · Executar

```bash
python .agents/encadeador/encadeador.py executar --manifesto corrente.json --trabalho meu-trabalho --dir tmp/recibos
```

**Rode em worktree ou clone descartável, nunca na árvore que importa** — a
etapa de sessão herda da receita de rotina o pular de permissões, porque
sessão agendada não tem quem responder prompt.

Saída: `0` = corrente completa, tudo `segue` · `5` = parou num `para` ·
`6` = parou num `pergunta`, aguardando o dono · `2` = erro de uso.

## 4 · Ler o resultado

Os recibos ficam em `<dir>/<trabalho>/`, um JSON por etapa, na ordem da
lista — com o log da conferência ao lado. Recibo `para` traz as `faltas` e
o `proximo` escrito por quem reprovou: reexecutar com ele é decisão de quem
opera, nunca automática. Com `teto` recibos `para` no diretório, nada mais
roda — a corrente escala para o dono em vez de insistir.

## O que o motor não faz — de propósito

- Não isola etapas entre si: fork que escreve no mesmo arquivo é corrida —
  o isolamento (worktree por etapa) é de quem escreve o manifesto.
- Não reordena manifesto de trabalho já rodado: a numeração dos recibos vem
  da posição na lista — reordenar começa outra série.
- Não empurra, não publica e não toca na automação da casa: portão e
  destrutivo são do dono.

A lista completa dos limites, com as medições, está no docstring de
`.agents/encadeador/encadeador.py`; o contrato do recibo, em
`.agents/recibo/recibo.schema.json`.
