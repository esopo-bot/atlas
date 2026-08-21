# O roteiro de entrega — um EXEMPLO, não o processo do seu repositório

`entrega.json`, ao lado, mostra a forma de um trabalho que termina em pedido
de revisão. **Ele é exemplo, e cada nome dentro dele sai da configuração** —
a camada não tem opinião sobre a topologia do seu repositório.

## O que ele demonstra

Seis estágios: abrir a branch de trabalho a partir da base declarada →
trabalhar → medir se o resultado entra na branch de integração declarada →
verificação → escrever o corpo do pedido de revisão → aprovação manual.

**Nada disso é obrigatório.** Se o seu repositório entrega direto na base,
apague os estágios do meio; se não usa branch de integração, tire o estágio
que mede o merge. O que o exemplo ensina não é a topologia — é que **a
automação nunca toca branch de longa duração**, e que o corpo do pedido
cobre o que o diff entrega.

## O que sai da configuração, e nunca do roteiro

| No roteiro | De onde vem |
| --- | --- |
| a base da branch de trabalho | `branches.base` |
| o nome da branch | `branches.padrao_de_trabalho` |
| onde o trabalho é medido | `branches.integracao` |
| o que a automação pode fazer | `autorizacoes`, em `nucleo/configuracao.json` |

Troque a configuração e o mesmo roteiro serve outro repositório. É esse o
teste de que ele é mecanismo, e não o processo de alguém.

## As quatro seções do pedido de revisão

O estágio que escreve o corpo exige, com estes títulos: **o que foi
testado** (comando e saída), **risco de quebrar em produção**, **mitigação**
e **plano de reversão** — incluindo o que a reversão *não* desfaz. Quem abre
o pedido é o dono, com o texto na mão.
