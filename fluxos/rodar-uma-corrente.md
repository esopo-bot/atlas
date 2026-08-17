# Rodar uma corrente

O passo a passo do motor opcional (módulo `encadeador`): uma corrente de
etapas, um recibo por etapa. Quem só usa as skills não precisa desta página.

## Antes de tudo — uma vez por casa

```bash
python montar.py --modulo encadeador
python .agents/recibo/recibo.py --testar
python .agents/conferir/conferir.py --testar
python .agents/encadeador/encadeador.py --testar
```

Os três `--testar` são o primeiro comando de qualquer retomada.

## 1 · O manifesto

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

| Tipo | O que faz |
| --- | --- |
| `codigo` | roda um comando; o stdout tem de ser um recibo válido |
| `sessao` | roda `claude -p` — regras da camada e `configuracao-da-casa.md` entram na frente, por código |
| `conferencia` | re-executa o `provado` dos recibos desta execução e acusa divergência |
| `portao` | espera o arquivo de aprovação do dono |

Etapas sem dependência entre si rodam juntas (fork); `conferencia` e
`portao` nunca dividem onda.

## 2 · O ensaio — sempre antes

```bash
python .agents/encadeador/encadeador.py ensaio --manifesto corrente.json --trabalho meu-trabalho
```

Lista as ondas sem executar nada.

## 3 · Executar

```bash
python .agents/encadeador/encadeador.py executar --manifesto corrente.json --trabalho meu-trabalho --dir tmp/recibos
```

**Rode em worktree ou clone descartável** — a etapa de sessão pula
permissões, porque sessão agendada não tem quem responder prompt.

Saída: `0` completa · `5` parou num `para` · `6` aguardando o dono ·
`2` erro de uso.

## 4 · Acompanhar o andamento

```bash
python .agents/encadeador/encadeador.py andamento --trabalho meu-trabalho --dir tmp/recibos
```

Fotografa os recibos e devolve JSON (contrato completo no docstring do
`encadeador.py`): por etapa — `nome`, `veredito`, `ciclo {i, teto}`,
`faltas`, `proximo` —, mais `estado`, `paras` (o contador do teto) e
`proxima_acao`. Com `--manifesto corrente.json`, `completa` vira prova:
toda etapa ligada precisa ter recibo `segue`.

| `estado` | O que fazer |
| --- | --- |
| `completa` | nada — leia os recibos em `<dir>/<trabalho>/` |
| `parada` | siga a `proxima_acao`: é o `proximo` de quem reprovou; reexecutar é decisão de quem opera |
| `aguardando-portao` | a `proxima_acao` diz qual arquivo de aprovação criar — decisão do dono |
| `em-curso` | nada rodou ainda (ou a foto pegou onda parcial — releia) |

Com `teto` recibos `para`, nada mais roda — a corrente escala para o dono.

## O que o motor não faz — de propósito

- Não isola etapas entre si: worktree por etapa é de quem escreve o
  manifesto.
- Não reordena manifesto de trabalho já rodado: a numeração vem da posição
  — reordenar começa outra série.
- Não empurra, não publica, não toca na automação da casa.

A lista completa dos limites está no docstring de
`.agents/encadeador/encadeador.py`; o contrato do recibo, em
`.agents/recibo/recibo.schema.json`.
