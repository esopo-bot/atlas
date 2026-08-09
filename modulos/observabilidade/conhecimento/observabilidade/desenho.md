# O desenho das aplicações

**Você escreve esta página. A skill só lê.** É a única peça da memória que não
se descobre investigando — e é a que mais rende: com ela, o copiloto manda
olhar a aplicação vizinha antes de você pensar nela.

Sem esta página, a skill perde exatamente duas coisas, e avisa na primeira
mensagem quando isso acontece:

- para de apontar aplicação vizinha quando o sintoma está numa ponta e a
  causa na outra;
- volta a perguntar do zero o que já poderia saber.

A skill pode **propor** um acréscimo quando um incidente revelar uma ligação.
Ela propõe; quem escreve é você.

---

## Quem chama quem

Apague as linhas de exemplo. Os nomes abaixo são inventados de propósito —
uma fábrica de chapéus que não existe.

| Aplicação | O que ela faz | Chama | É chamada por |
| --- | --- | --- | --- |
| `vitrine` | a tela que o cliente vê | `chapelaria`, `carteiro` | ninguém (é a ponta) |
| `chapelaria` | monta o pedido e reserva peça | `almoxarifado` | `vitrine` |
| `almoxarifado` | estoque e reserva | banco, `porteiro` | `chapelaria` |
| `carteiro` | envia aviso ao cliente | serviço externo de mensagem | `vitrine`, `chapelaria` |
| `porteiro` | autenticação | — | todas |

## Onde cada uma vive

| Aplicação | Serviço na ferramenta | Ambientes |
| --- | --- | --- |
| `vitrine` | `vitrine-web` | `producao`, `homologacao` |
| `chapelaria` | `chapelaria-api` | `producao`, `homologacao` |
| `almoxarifado` | `almoxarifado-api` | `producao` |

O nome do serviço na ferramenta quase nunca é o nome da aplicação. Esta
coluna é a que mais economiza tempo: sem ela, a consulta sai com o nome
errado e devolve vazio honesto.

## O que atravessa tudo

| Coisa compartilhada | Quem depende | Quando ela cai |
| --- | --- | --- |
| `porteiro` | todas | tudo devolve 401 ao mesmo tempo |
| banco do `almoxarifado` | `almoxarifado`, `chapelaria` | pedido trava, vitrine responde lento |

Esta tabela é a que responde "por que três aplicações quebraram juntas?".
