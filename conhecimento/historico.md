# O histórico das issues encerradas

Quando uma issue fecha, o trabalho dela vira um `.md` local, numa pasta por
projeto, em `conhecimento/issues_encerradas/<projeto>/<numero>-<assunto>.md`.
É o registro do que foi pedido, feito e provado, e ele fica indexado: o
trabalho seguinte o acha pela busca do acervo, em vez de redescobrir o que já
se sabia.

## Como se usa

```bash
python .agents/historico/historico.py --pendentes     # quantas fecharam sem histórico
python .agents/historico/historico.py --colher        # grava o das pendentes
python .agents/historico/historico.py --issue <numero> --ensaio   # mostra sem gravar
```

O `--abertura` do `camada.py` roda o `--pendentes` e acusa a issue fechada
sem histórico. A issue fecha no rastreador, quase sempre pelo `Closes` do
pedido que o dono mescla, às vezes à mão, e nenhuma sessão está aberta nessa
hora. Por isso o histórico se colhe por puxada, na sessão seguinte, e os dois
caminhos de fechamento contam igual: o instrumento olha o estado `closed` da
issue, não o pedido mesclado.

## O que o instrumento garante

- **Só daqui para frente, desde a chegada.** Issue fechada antes do marco
  não se colhe. O marco é a data do commit que trouxe o instrumento a este
  checkout, lida do git pelo caminho do próprio arquivo — quem recebe o
  módulo tarde, por um `git pull`, não perde o que fechou entre a chegada e
  a primeira execução. Se o arquivo chegou mais de uma vez, vale a primeira:
  a sobra aparece como pendência, a falta sumiria calada. A primeira execução
  grava o marco em `conhecimento/issues_encerradas/.desde`, e dali em diante
  o `.desde` vale sempre; para adiantar a data, reescreva-o. Sem commit do
  instrumento, ou sem git, o marco é a primeira execução.
- **Na árvore principal.** De dentro de uma worktree ele grava na raiz de
  onde ela saiu: a pasta é ignorada pelo git, e gravada na worktree sumiria
  com ela.
- **Fora do git.** Ele só grava onde o git ignora. Quem instala a camada
  recebe o `.gitignore` dentro da pasta; o índice continua lendo o que está
  lá, porque o servidor lê só o arquivo de ignorar da raiz de cada alvo.
- **Sem segredo.** Antes de gravar, ele confere o texto por forma de segredo
  — token, chave, senha escrita por extenso, e-mail — e recusa dizendo a
  linha e a forma, nunca o valor. Nenhum gancho confere o que se grava em
  arquivo, então a conferência mora nele.
- **Critério em branco não vira pronto.** O `Closes` fecha a issue sem ler os
  critérios. O histórico copia os critérios como estavam e diz quantos
  ficaram em branco.
- **Reindexa.** Depois de gravar, ele pede a ronda do índice.

## O que guardar, e onde

O histórico é destilado do **corpo final** da issue, que é a fonte única. Ele
aponta para onde cada coisa mora, sem copiar o que tem outro lugar:

| o que | onde mora | o histórico guarda |
| --- | --- | --- |
| o que foi pedido, feito e provado | o próprio histórico | inteiro, com o pedido que fechou e os commits da marca `(issue N)` |
| decisão do dono | o próprio histórico | inteira, com data e motivo |
| valor de credencial | `.credenciais/acessos/` | só o ponteiro |
| conta de teste, estado salvo de navegador | uma linha em `.credenciais/INVENTARIO.md`, sem valor | papel, ambiente e ponteiro |
| fato durável do vizinho: comando, ambiente, armadilha | o perfil em `conhecimento/projetos/<projeto>.md`, fora da seção que o dono declarou | o link |
| lição que serve a qualquer repositório | uma linha na caixa (`caixa.py melhoria`) | o link |

Antes de fechar, a sessão escreve no corpo a seção
`## Onde mora o que se aprendeu`, com esses ponteiros; o instrumento a copia
para o histórico. Corpo sem ela gera histórico que diz que o ponteiro faltou.

## A gaveta de credenciais

O ritual de fechamento lê e escreve em `.credenciais/`, e sempre por
roteiro: o valor entra pelo `stdin` e sai para o arquivo, nunca pela tela,
pelo `echo`, pelo transcript, pelo git, pela issue ou pelo histórico. O que
se lê em voz alta é o nome, nunca o valor.

## De onde vem o projeto

A pasta do projeto é a etiqueta da issue que também é chave do cadastro de
projetos em `nucleo/executor.json`. Issue sem etiqueta cadastrada vai para
`sem-projeto/` — etiquete-a e colha de novo.
