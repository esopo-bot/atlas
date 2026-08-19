# Roteiros que viajam com a camada

Esta pasta é o oposto da `execucoes/` da raiz: **aqui o conteúdo ENTRA no
git**, e é essa a razão de ela existir.

Roteiro que mora aqui é **da camada**: não sabe nada de ninguém, tira todo
endereço da configuração, e serve a qualquer repositório que instale o
módulo. Troque a configuração e o mesmo roteiro serve outro lugar — é esse o
teste de que ele é mecanismo, e não o processo de alguém.

| Roteiro | O que faz | A página |
| --- | --- | --- |
| `catalogador.json` | reorganiza a camada de conhecimento e as anotações | `catalogador.md` |
| `entrega.json` | exemplo de trabalho que termina em pedido de revisão | `entrega.md` |

O `.gitignore` ao lado ignora tudo e **libera por nome**, um roteiro por
linha — nunca `!*.json`, que reabriria a pasta e deixaria roteiro local
vazar sem ninguém ver.

## Onde mora o SEU roteiro

Na `execucoes/` da raiz do seu repositório. Lá o conteúdo não entra no git,
de propósito: roteiro de trabalho cita o caminho da sua máquina, o nome dos
seus outros repositórios, o seu caso. Nada disso viaja.

Quando um roteiro seu deixar de citar o seu caso e passar a servir qualquer
repositório, ele é candidato a mudar para cá — e aí precisa da linha no
`.gitignore` e da página ao lado.
