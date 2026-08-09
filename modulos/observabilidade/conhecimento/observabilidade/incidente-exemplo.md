# 2026-03-11 — pedido travado na chapelaria

Molde de registro de incidente. A skill cria um
`incidente-<data>-<slug>.md` ao encerrar, com o que **você aprovou** guardar.
Fábrica de chapéus inventada — apague.

Este arquivo **não entra na abertura da sessão**. Procura-se quando o sintoma
parecer conhecido, e só então.

| | |
| --- | --- |
| Sintoma, nas palavras de quem viu | "o pedido fica processando e não sai" |
| Aplicações envolvidas | `chapelaria`, `almoxarifado` |
| Padrão da mensagem | `deadline exceeded ao reservar <peça>` |
| O que era | reserva no estoque esperando bloqueio de banco que ninguém soltava |
| Como se achou | rastreamento inteiro pelo `dd.trace_id`, no salto para `almoxarifado` |
| Quanto tempo até achar | ~40 min, dos quais ~25 em caminho morto |

## O que provou cada coisa

| Achado | O que provou |
| --- | --- |
| a espera é no `almoxarifado`, não aqui | rastreamento mostrou o salto com o tempo todo do lado de lá |
| começou às 08:02 | contagem por período: zero antes, dezenas depois |
| não foi implantação | nenhuma implantação nas 12h anteriores |

## Caminhos que não deram em nada

| Caminho | Por que não deu |
| --- | --- |
| procurar `timeout` na mensagem | a aplicação escreve `deadline exceeded` |
| olhar o nível `error` | a espera saía como `warn` |
| janela de 15 min | o registro chega em lote a cada 5 min; a janela pegava antes |

Esta seção é a que economiza a segunda meia hora. Ela é a razão de o registro
existir — o "o que era" qualquer um lembra.

## O que ficou sem prova

- por que o bloqueio não foi solto: ninguém olhou o banco a tempo;
- se o processamento em lote das 8h é a causa ou só coincide com ela.
