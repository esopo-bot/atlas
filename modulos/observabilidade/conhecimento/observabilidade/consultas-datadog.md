# Caderno de consultas — Datadog

A que funcionou, **e a que mentiu** — as duas importam. O porquê do formato,
e o de guardar as que falharam: `references/ingestao.md` da skill.

Os exemplos abaixo são de uma fábrica de chapéus que não existe. Apague-os.

## As que funcionam

| Consulta | Responde o quê | Por que não é a óbvia | Quando mente |
| --- | --- | --- | --- |
| `env:producao service:chapelaria-api status:error` | os erros da aplicação de pedidos | o serviço se chama `chapelaria-api`, não `chapelaria` — o nome da aplicação não existe na ferramenta | sem `env`, mistura homologação e parece o dobro do volume |
| `env:producao service:almoxarifado-api @http.status_code:[400 TO 499]` | recusa do cliente, separada de falha nossa | `status:error` não pega 4xx: a aplicação registra 4xx como `info` | se a aplicação passar a registrar 4xx como `warn`, continua certa — é o código que filtra, não o nível |

## As que mentiram — não repita

| Consulta | Parecia certa porque | Devolveu | O que era |
| --- | --- | --- | --- |
| `service:chapelaria status:error` | é o nome da aplicação | vazio | o serviço registrado é `chapelaria-api` |
| `service:carteiro-api status:error` (janela de 15 min) | o erro tinha acabado de acontecer | vazio | a aplicação envia registro em lote a cada 5 min; janela curta pega antes da chegada |

A última linha é o gênero mais caro: **vazio que vira verdade em dez minutos**.
Antes de escrever "não existe", alargue a janela e refaça.

O formato da entrada — cinco campos, com o porquê de cada um — está em
`references/ingestao.md` da skill; a sintaxe canônica, na tabela de
[observabilidade](../observabilidade.md). O caderno guarda só o que é do
workspace.
