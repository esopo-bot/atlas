# Revisão geral do diff — correção antes da entrega

Revise o diff desta branch de trabalho atrás de DEFEITO DE CORREÇÃO: o que
quebra, mente, vaza ou perde dado. Estilo e idiomatismo não são seus — a
régua da stack é de outra etapa, e cerca cobrada duas vezes é ruído.

O QUE REVISAR. Só o diff da branch contra a base declarada em
`branches.base` do `nucleo/executor.json` — `git diff origin/<base>...HEAD`.
Código que a branch não tocou não é o assunto.

A FERRAMENTA. Invoque a skill `code-review` com o argumento `low` — ela é do
harness da sessão e existe em qualquer repositório, medido. Nível `low`
aponta pouco e com confiança, que é o que uma rodada automatizada aguenta
sem afogar em achado especulativo. Se a invocação falhar, diga isso em
`suposto` e revise você mesmo, pela leitura do diff — a etapa não quebra
porque a ferramenta faltou, mas também não finge que ela rodou.

O QUE VOCÊ NÃO PODE FAZER NESTA ETAPA: escrever código, commitar, empurrar
ou mexer na branch. Esta etapa LÊ e opina; consertar é de quem trabalha, na
retomada.

O VEREDITO. `para`, com o `proximo` dizendo o conserto em uma linha, quando
a revisão confirmar defeito de correção no diff — cada achado nomeando
arquivo e linha. `segue`, com os achados menores em `suposto`, quando nada
justificar parar antes da entrega.

A PROVA: cada afirmação sua tem comando e saída COLADA do terminal, e a
prova se ancora em COMMIT, nunca em nome de branch. `git merge-base
origin/<base> HEAD` dá o sha da base da mescla e `git rev-parse HEAD` o da
cabeça; o que entra no provado é `git diff --stat <sha-da-base>
<sha-da-cabeça>`. `origin/<base>` anda enquanto OUTRA execução mescla, e
prova que o cita deixa de reproduzir com o trabalho estando certo — a
verificação acusa e a retomada custa um ciclo. A lista de achados da
revisão — ou a lista vazia — colada prova o que ela disse. Afirmação de
revisor sem comando é opinião vestida de medida.
