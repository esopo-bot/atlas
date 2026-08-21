# Auditor: quem verifica a execução lê evidência, não comportamento

Depois que o executor de roteiros roda, sobra uma pasta de evidências — uma
por etapa. O auditor lê essa pasta e responde três perguntas que ninguém
responde de graça: **o que aconteceu, o que ainda reproduz, e o que isso
sugere.**

## Por que ele não observa a sessão

A tentação é pôr uma sessão para assistir a outra e dizer onde ela errou.
Isso não funciona, e o motivo é a regra 2: *"o modelo disse" não é prova*. Uma
sessão narrando outra devolve texto plausível sobre comportamento que ela não
mediu — exatamente o que a camada inteira existe para evitar.

O auditor faz o contrário: **só fala do que ficou escrito**. A evidência é o
que a etapa declarou, e a re-execução é o que ainda se sustenta. O resto ele
marca como leitura.

## As duas partes do relatório, e por que se separam

| Parte | O que entra | Como se lê |
| --- | --- | --- |
| **PROVADO** | veredito, ciclo, faltas, e o que o verificador re-executou | fato |
| **SUPOSTO** | onde a execução parou, quem repetiu, quem seguiu sem prova | leitura |

Misturar as duas é o defeito clássico do relatório automático: ele soa
confiante sobre a metade que inventou. Separadas, a opinião pode existir sem
se disfarçar.

## O que ele aponta, e por que cada coisa importa

- **Etapa que gastou mais de um ciclo.** Repetir não é falha — é sinal de que
  o critério não estava claro na primeira passada. É o melhor lugar para
  melhorar o roteiro.
- **Evidência escrita pelo motor, não pela etapa.** Quando a etapa morre,
  estoura o tempo ou devolve algo inválido, quem dá nome ao estado é o motor.
  Toda evidência assim é uma etapa que não conseguiu se explicar.
- **Etapa que seguiu sem nenhum item provado.** É a regra 2 sendo contornada
  por dentro: veredito de sucesso sem nada que o sustente.
- **Prova que não reproduz mais.** O comando estava lá, a saída estava lá, e
  agora dão outra coisa. Ou o mundo mudou, ou a prova foi redigida em vez de
  colada.

## Auditoria não é guarda

A distinção decide onde cada coisa mora:

- **Guarda** é barata, determinística e **roda sempre** — gancho que recusa,
  rotina que reprova no ritual. Ela vale justamente porque não dá para pular.
- **Auditoria** é cara e narrativa, e **roda quando alguém liga**.

Mudar uma guarda para dentro de um módulo opcional é perder a guarda. Por isso
o auditor não recebe o que já é cobrado sempre: ele acrescenta leitura, não
substitui recusa.

## O limite, declarado

Ele lê o que terminou. Não acompanha ao vivo, etapa a etapa, e não sabe nada
do que a sessão pensou — só do que ela deixou escrito. Uma etapa que erra e
não registra nada é, para o auditor, uma etapa que não existiu.

A evidência nasce na execução, uma etapa antes.
