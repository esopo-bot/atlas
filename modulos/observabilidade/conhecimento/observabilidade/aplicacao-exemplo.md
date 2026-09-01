# chapelaria — molde de página de aplicação

Este arquivo é o **molde**. A skill cria um `aplicacao-<nome>.md` por
aplicação, no primeiro incidente que tocar nela. `chapelaria` é uma fábrica de
chapéus que não existe — apague quando a primeira aplicação de verdade nascer
aqui.

Mantenha a forma: tabela e lista. Prosa só onde o porquê não couber numa
célula.

| | |
| --- | --- |
| O que faz | monta o pedido e reserva a peça no estoque |
| Serviço na ferramenta | `chapelaria-api` |
| Ambientes | `producao`, `homologacao` |
| Fala com | `almoxarifado` (reserva), `porteiro` (autenticação) |
| Quem depende dela | `vitrine` |

## Sintomas conhecidos

| Sintoma | Onde olhar | Costumou ser |
| --- | --- | --- |
| pedido fica "processando" e não sai | rastreamento do `dd.trace_id`, no salto para `almoxarifado` | espera de reserva no estoque, não erro |
| 401 em rajada, em tudo | `porteiro`, não aqui | rotação de chave no autenticador |
| lentidão só de manhã | contagem por período, janela de 24h | processamento em lote do `almoxarifado` às 8h |

## Caminhos mortos

| Caminho | Por que não dá | Quando se viu |
| --- | --- | --- |
| procurar por `timeout` na mensagem | a aplicação registra `deadline exceeded` | 2026-03-11 |
| olhar o nível `error` para achar recusa do cliente | 4xx sai como `info` | 2026-03-11 |
| filtrar pelo nome `chapelaria` | o serviço é `chapelaria-api` | 2026-01-04 |

## Consultas que servem a esta aplicação

Ficam no [caderno](consultas-datadog.md), não aqui — uma consulta mora num
lugar só. Aqui vai o ponteiro:

- os erros dela, separados de recusa do cliente;
- o rastreamento do salto para `almoxarifado`.

## O que ainda não se sabe

- se a espera de reserva tem teto configurado, e qual;
- se o processamento em lote das 8h pode ser adiado.

Esta seção existe para a lacuna não virar suposição. Buraco escrito é buraco
que alguém fecha; buraco esquecido vira "acho que é assim".
