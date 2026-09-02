# Investigação de incidente

Algo quebrou e a pergunta é "o que mudou?". A ordem abaixo estreita o campo
a cada passo; as armadilhas de medição, no fim, são o que faz uma conclusão
errada passar por prova.

## A ordem

1. **Reproduza o sintoma, com a chamada do cliente real.** Opção a mais na
   sua chamada percorre outro caminho e fabrica defeito. Não reproduziu? O
   primeiro trabalho é descobrir para quem acontece.
2. **Ache no código a mensagem que a pessoa vê** — o fio mais curto entre a
   tela e a linha.
3. **Extraia o identificador de rastreio.** Sem ele você lê log por horário —
   e lê o log errado.
4. **Ache a requisição exata**, inteira, com começo e fim.
5. **Ancore a linha do tempo**: não "está falhando?" — **"desde quando?"**,
   com contagem por período. Sem nomear o instante do começo, você ainda não
   investigou o suficiente para acusar nada.
6. **Diferencie o que mudou**, preferindo artefato imutável a memória: versão
   publicada, data de implantação, trilha de auditoria. Quatro suspeitos:
   código, configuração, infraestrutura, rede.
7. **Separe defeito seu de dependência externa** — muda o que se faz a
   seguir.
8. **Rode o cético** (skill `verificacao-adversarial`) antes de concluir.
9. **Conclua — e diga o que ficou sem prova.**

O raciocínio que fecha: código idêntico + infraestrutura idêntica + hora exata
de uma mudança de configuração = a configuração é a variável.

Os passos 3 a 7 mudam de forma conforme a ferramenta de observabilidade; os
outros quatro não mudam. As armadilhas abaixo mordem principalmente nos
passos 3 e 5.

## O pedido que se leva a quem pode consertar

Quando o defeito é do outro lado da fronteira, o que se manda vale mais que o
quanto se manda:

| O que entra | Por quê |
| --- | --- |
| o sintoma em uma frase, do ponto de vista de quem usa | quem recebe reconhece o problema como real |
| o escopo **medido** — quantos afetados sobre quantos tentaram | amostra pequena vira prioridade baixa, e quem não reclama some da conta |
| o instante exato em que começou | sem ele não se sabe onde procurar |
| identificadores que **quem recebe** consegue procurar | o seu identificador não serve na ferramenta de quem recebe |
| o que mudou do seu lado, com hora | antecipa a pergunta de volta |
| **o pedido acionável**: o que verificar, e o que fazer em cada resultado | evidência sem pedido é meia entrega |
| como a correção será validada em tempo real | fecha sem segunda rodada |

Sem acusação e sem adjetivo. O que não estiver medido entra como "não
medido" — nunca estimado.

## As armadilhas de medição

## Retenção é parte da prova

Todo log, toda métrica e todo rastro tem uma janela de retenção. Antes de
concluir qualquer coisa a partir de uma busca, confira se o período pedido cabe
dentro da janela — sem isso, a busca não prova nada sobre o que aconteceu antes
dela.

## "Não achei" fora da janela não significa nada

Buscar um identificador e não encontrá-lo só é evidência de ausência quando a
busca cobriu o período inteiro em que o evento poderia ter acontecido. Fora da
janela de retenção, "não achei" quer dizer "não sei" — nunca "não aconteceu".

## Ausência de linha não é ausência de falha

Sistema que não grava toda categoria de evento tem zero na tabela mesmo quando
o evento aconteceu. Antes de tratar um zero como fato, confirme que o
instrumento realmente registraria o que se procura — comparando com uma
categoria vizinha de volume conhecido, por exemplo.

## O identificador da requisição costuma dizer a hora em que ela começou

Muitos formatos de identificador de rastreio (trace id, request id) embutem um
carimbo de tempo. Antes de assumir que o evento é recente, ou de descartá-lo
por estar fora de uma janela estimada, decodifique o identificador — ele pode
apontar para um instante bem mais antigo do que a hora em que foi observado.
