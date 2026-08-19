# Investigação de incidente

Algo quebrou em produção e a pergunta é "o que mudou?". Siga a ordem —
cada passo estreita o campo.

## A ordem

1. **Reproduza o sintoma, com a chamada do cliente real.** Opção a mais na
   sua chamada percorre outro caminho e fabrica defeito. Não reproduziu? O
   primeiro trabalho é descobrir para quem acontece.
2. **Ache no código a mensagem que o usuário vê** — o fio mais curto entre
   a tela e a linha.
3. **Extraia o identificador de rastreio.** Sem ele você lê log por horário
   — e lê o log errado.
4. **Ache a requisição exata**, inteira, com começo e fim.
5. **Ancore a linha do tempo**: não "está falhando?" — **"desde quando?"**,
   com contagem por período. Sem nomear o instante do começo, você ainda
   não investigou o suficiente para acusar nada.
6. **Diferencie o que mudou**, preferindo artefato imutável a memória:
   versão publicada, data de implantação, trilha de auditoria. Quatro
   suspeitos: código, configuração, infraestrutura, rede.
7. **Separe defeito nosso de dependência externa** — muda a quem você
   escala.
8. **Rode o cético** (skill `cetico`) antes de concluir.
9. **Conclua — e diga o que ficou sem prova.**

O raciocínio que fecha: código idêntico + infraestrutura idêntica + hora
exata de uma mudança de configuração = a configuração é a variável.

## A mensagem de escalação

| O que entra | Por quê |
| --- | --- |
| o sintoma em uma frase, do ponto de vista de quem usa | o outro time reconhece o problema como real |
| o escopo **medido**: afetados sobre quantos tentaram | amostra despriorizada mata incidente — quem não reclama some da conta |
| o instante exato em que começou | sem ele não sabem onde procurar |
| identificadores que **eles** conseguem procurar | o seu não serve no painel de controle do outro |
| o que mudou do nosso lado, com hora e autor | antecipa a pergunta de volta |
| **o pedido acionável**: o que verificar, e o que fazer em cada resultado | evidência sem pedido é escalação pela metade |
| como a correção será validada em tempo real | fecha sem segunda rodada |

Sem acusação e sem adjetivo. O que não estiver medido entra como "não
medido" — nunca estimado.

Busca que devolve zero e log noutro vocabulário:
[falso negativo](../conhecimento/falso-negativo.md) — leia antes de
confiar num vazio.
