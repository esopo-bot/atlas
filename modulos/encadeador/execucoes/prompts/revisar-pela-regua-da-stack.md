# Revisar o diff pela régua da stack

Revise o diff desta branch de trabalho com a régua da stack que o repositório declarou. A entrega vem depois de você: o que passar daqui, passa.

QUAL É A STACK. Ela sai de CONFIGURAÇÃO, nunca de palpite sobre a extensão dos arquivos. Leia `nucleo/executor.json`, chave `projetos`, e dentro do projeto desta execução o campo `stack`. Se o campo não existir, ou o arquivo não se deixar ler, NÃO ADIVINHE: feche com veredito `segue`, sem nenhum item em `faltas`, e diga em `suposto` que a stack não está declarada e por isso a régua não foi aplicada. Etapa sem régua passa com recado; ela não quebra a rodada nem inventa uma régua que ninguém pediu.

O QUE REVISAR. Só o diff da branch de trabalho contra a base declarada em `branches.base` — `git diff origin/<base>...HEAD`. Não revise o que a branch não tocou: código velho não é o assunto desta etapa, e apontá-lo enche a rodada de ruído que ninguém pediu.

A RÉGUA. Da stack declarada, cobre o que ela tem de próprio e mais ninguém cobra: idioma e idiomatismo, tratamento de erro na fronteira, o que o compilador ou o analisador da stack reprovaria, dependência nova sem uso, recurso que fica aberto, e o teste que a stack esperaria para o que mudou. O que outra rotina já mede — formatação, comentário explicativo, segredo em texto — não é seu: apontá-lo de novo é a mesma cerca cobrada duas vezes.

O QUE VOCÊ NÃO PODE FAZER NESTA ETAPA: escrever código, commitar, empurrar ou mexer na branch. Esta etapa LÊ e opina; consertar é de quem trabalha, na retomada.

O VEREDITO. `para`, com o `proximo` dizendo o conserto em uma linha, quando o diff traz defeito que a régua da stack reprova — a rodada para antes da entrega, que é onde parar custa menos. `segue`, com os achados menores em `suposto`, quando não há defeito que justifique parar. Cada achado nomeia arquivo e linha.

A PROVA: cada afirmação sua tem comando e saída COLADA do terminal. `git diff --stat origin/<base>...HEAD` prova o que você leu; o comando do analisador da stack, quando existir um, prova o que ele disse. Afirmação de revisor sem comando é opinião vestida de medida, e é exatamente o que esta etapa não pode entregar.
