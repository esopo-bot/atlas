# insights

Dispara uma consulta do **CloudWatch Logs Insights** e devolve o resultado já
em colunas. Um comando faz os três passos que se escreviam à mão toda vez —
`start-query`, esperar em laço até `Complete`, extrair — e a extração funciona
igual para consulta de `stats` e de `fields`, o formato que voltava vazio sem
erro nenhum.

```bash
python montar.py --modulo insights
```

Ele **conecta e roda** — ao contrário do módulo `observabilidade`, que ensina
a consultar sem tocar na ferramenta. Por isso é um módulo à parte: quem quer o
copiloto que não se conecta instala aquele; quem quer o atalho que dispara
instala este.

## O que ele instala

| Destino | O que é |
| --- | --- |
| `.agents/insights/insights.py` | o instrumento: recebe grupo, região, consulta e janela por argumento, e devolve colunas |

## A linha vermelha

Nenhum valor de cliente nasce dentro dele: não há grupo de log padrão, região
padrão nem nome de rota. Tudo entra por argumento. No dia em que um valor de
cliente for embutido, ele deixa de ser genérico e vira material de um
workspace — e material de workspace mora lá, não numa camada que viaja para
todos.

## Como se usa

```bash
python .agents/insights/insights.py \
  --grupo "${GRUPO_DE_LOG}" --regiao "${REGIAO}" \
  --consulta 'fields @timestamp, @message | filter @message like /erro/ | limit 20' \
  --desde 2h
```

A janela nunca se escreve em epoch à mão: `--ate` vale `agora` quando
omitido, e `--desde` aceita uma duração para trás (`30m`, `2h`, `1d`), além
de ISO 8601 e epoch em segundos. `--json` troca as colunas por JSON. `--teto`
sobe o tempo de espera quando a janela é larga. A credencial é a que o `aws`
já usa nesta máquina — o instrumento não a toca.

## As três idas que ele economiza

Cada uma custou uma volta ao terminal antes de virar código:

- **`--cli-read-timeout` em toda chamada** (`--tempo-de-leitura`, 120 s por
  padrão): sem ele o `aws` desiste de ler a resposta antes de o Insights
  responder, e a consulta parece muda quando só está lenta.
- **O epoch calculado, não digitado**: `--desde 2h` é a conta que se fazia
  com `date` toda vez, e errava.
- **Aviso da colisão de alias do `parse`**: alias que repete outro `parse`,
  ou que tem o mesmo nome de um campo do `fields`, cala o original sem erro
  nenhum. O instrumento avisa em stderr antes de disparar; a consulta segue.
