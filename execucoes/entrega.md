# O roteiro de entrega — um EXEMPLO, não o processo do seu repositório

`entrega.json`, ao lado, mostra a forma de um trabalho que termina em pedido
de revisão. **Ele é exemplo, e cada nome dentro dele sai da configuração** —
a camada não tem opinião sobre a topologia do seu repositório.

## O que ele demonstra

Nove estágios: abrir a branch de trabalho a partir da base declarada →
trabalhar → medir se o trabalho foi commitado → **empurrar a branch para o
repositório durável** → **revisar o diff pela régua da stack** → medir se o
resultado entra na branch de integração declarada → verificação → escrever o
corpo do pedido de revisão → aprovação manual.

O estágio que revisa pela régua da stack lê a stack de CONFIGURAÇÃO —
`projetos.<projeto>.stack`, em `nucleo/executor.json` —, nunca da extensão dos
arquivos. Sem stack declarada ele passa com recado, em vez de quebrar a rodada
ou inventar uma régua que ninguém pediu: a camada não tem opinião sobre a
stack de quem instala. Ele lê e opina; consertar é de quem trabalha.

O estágio que empurra existe por uma medição: a árvore de trabalho costuma
ser descartável — em muitas máquinas `/tmp` é memória, não disco — e trabalho
commitado que nunca saiu dela some com ela, sem log e sem aviso. O estágio
empurra assim que o commit existe e prova o destino com
`git ls-remote --heads origin <branch>`; se a branch não chegou, ele reprova
e a execução para ali, antes de qualquer espera.

**Nada disso é obrigatório.** Se o seu repositório entrega direto na base,
apague os estágios do meio; se não usa branch de integração, tire o estágio
que mede o merge. O que o exemplo ensina não é a topologia — é que **a
fronteira é de etapa, não de sempre**: a etapa de trabalho só commita na
branch de trabalho, e quem leva o resultado para a branch de integração
declarada é a ENTREGA, depois da aprovação manual. Mesclar a branch de
publicação e publicar seguem do dono, sempre. E o corpo do pedido cobre
o que o diff entrega.

## O que sai da configuração, e nunca do roteiro

| No roteiro | De onde vem |
| --- | --- |
| a base da branch de trabalho | `branches.base` |
| o nome da branch | `branches.padrao_de_trabalho` |
| onde o trabalho é medido | `branches.integracao` |
| o que a automação pode fazer | `autorizacoes`, em `nucleo/configuracao.json` |
| a régua do revisor de diff | `projetos.<projeto>.stack` |

Troque a configuração e o mesmo roteiro serve outro repositório. É esse o
teste de que ele é mecanismo, e não o processo de alguém.

## As quatro seções do pedido de revisão

O estágio que escreve o corpo exige, com estes títulos: **o que foi
testado** (comando e saída), **risco de quebrar em produção**, **mitigação**
e **plano de reversão** — incluindo o que a reversão *não* desfaz. Quem abre
o pedido é o dono, com o texto na mão.
