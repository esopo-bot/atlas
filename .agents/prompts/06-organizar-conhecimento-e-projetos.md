# Organize `conhecimento/` e `projetos/` pelas regras da camada

Prompt para qualquer agente aberto na raiz de um repositório que instalou a
camada. Cole inteiro. O objetivo: as duas pastas do workspace passam a ter a
forma que as regras pedem, sem perder uma linha do que o dono escreveu.

## A cerca que vale acima de tudo

- **Liste antes de mover.** Nada se move sem a lista inteira na tela.
- **Mover é `git mv`.** Nunca copiar e apagar. O que não está no git se
  move com `mv` e entra na lista de "fora do git" do relato.
- **Destino ocupado vira pergunta**, nunca sobrescrita.
- **Apagar é do dono.** Você propõe a lista do que sairia, com a razão de
  cada item; ele decide.
- **Anotação do dono não se toca.** Arquivo de anotações solto, rascunho
  dele, nota com o nome dele: fica onde está, e entra no relato como "do
  dono".
- **Nada de nome de pessoa, empresa, máquina ou credencial** em arquivo que
  a camada rastreie. O que for do trabalho fica na pasta do trabalho.

## Três origens de sujeira, três tratamentos

Antes de julgar arquivo por arquivo, descubra de onde ele veio. Cada origem
tem instrumento ou dono próprio, e misturar as três é o que faz o agente
apagar o que era do dono e poupar o que era lixo.

1. **Resto da versão anterior da camada** — página, gancho ou skill que a
   camada escrevia e deixou de escrever. Não é assunto deste prompt: a
   receita é o prompt `02` desta pasta, com `python3 .agents/limpeza/limpeza.py
   rodar --workspace .` listando antes de apagar. Rode o 02 primeiro, ou
   marque esses itens como "resto da camada — prompt 02" no inventário.
2. **Resto de sessão** — saída de comando na raiz, arquivo `.err`, prompt
   colado, cópia de teste de outro agente, script de uma vez só. O endereço
   é `tmp/`, que fica fora do git; o que já está em `tmp/` está no lugar e
   envelhece lá. O que está na raiz se move para `tmp/`; o que estava
   rastreado sai do git na mesma mudança.
3. **Material do dono fora de forma** — pasta de conhecimento, script de
   apoio, template, anotação. É o assunto deste prompt, pelas regras abaixo.

## As regras que dão a forma

Para `conhecimento/`:

1. **Um nível de subpasta.** Cada subpasta nasce com um `LEIAME.md` de uma
   linha dizendo o que mora ali. Subpasta dentro de subpasta se achata.
2. **Nome minúsculo, sem acento, sem espaço.** Prefixo numérico não é regra
   da camada nem contra ela: entra no plano como pergunta ao dono, com a
   forma sem prefixo ao lado.
3. **Um lugar por assunto.** O mesmo tema em duas páginas vira uma, e a que
   sobrevive é a que tem prova; a outra aponta para ela ou sai.
4. **Conhecimento nasce na língua de quem vai lê-lo** (regra 14): o que a
   sessão consome é dado estruturado, com campo nomeado; o que a pessoa lê é
   prosa por assunto, densa.
5. **A wiki dos vizinhos mora em `conhecimento/projetos/`**, um perfil por
   repositório, gerado pela skill `perfil-de-repositorio`. Perfil escrito à
   mão em outro lugar se move para lá.
6. **Trabalho em andamento não mora em arquivo**: mora na issue. Arquivo
   de andamento entra na lista de saída com a issue que o substitui.

Para `projetos/`:

1. **Uma pasta por repositório clonado, com o nome do repositório.** Nada
   mais mora aqui: script solto, arquivo de uma vez só e cópia de código de
   fora vão para `tmp/` ou para o repositório a que pertencem.
2. **`ls projetos/` é a lista do que existe.** A wiki em
   `conhecimento/projetos/` é o perfil; repositório sem perfil ganha um,
   perfil sem repositório entra na lista de saída.
3. **Só leitura é só leitura.** Repositório que a configuração declara
   como somente leitura não recebe escrita nenhuma, nem para organizar.

Para a raiz do repositório:

- Rascunho e arquivo gerado vão para `tmp/`. Script de apoio que só serve a
  este repositório mora numa pasta própria com `LEIAME.md` de uma linha; a
  pasta que já existe fica, e ganha o `LEIAME.md` se não tiver. Script que
  serve a um repositório vizinho vai para ele.
- Credencial fica onde está e fora do git: confira o `.gitignore`, nunca
  mova nem abra o conteúdo.
- Pasta nasce quando o material cansa a leitura, nunca por antecipação.

## O que você faz, nesta ordem

1. **Inventário**, sem mover nada: `git ls-files conhecimento projetos` e
   `ls -la` das duas pastas e da raiz. Cole a lista e marque cada item com a
   origem (1, 2 ou 3) e um destino: **fica**, **move para X**, **funde com
   Y**, **sai (do dono)**, **do dono, não se toca**, **pergunta**.
2. **Mostre o plano ao dono e espere o sim.** Plano sem sim não se executa.
3. **Execute só o que ele aprovou**, com `git mv`, um `LEIAME.md` por
   subpasta nova, e a correção dos links que apontavam para o caminho velho
   (`grep -rn` pelo caminho antigo, antes e depois).
4. **Prove:** `git status --short` colado; nenhum arquivo apagado; a rotina
   de referências órfãs, se o repositório a tiver, sem acusação nova.
5. **Relate:** o que moveu, o que fundiu, o que ficou por decisão, o que é
   do dono, e a lista de saída — com a razão de cada item.

## O que você NÃO faz

Não apaga. Não edita cópia da camada. Não toca em repositório declarado como
somente leitura. Não commita sem o repositório autorizar em
`nucleo/configuracao.json`. Não escreve nome de pessoa, empresa ou máquina em
nada que a camada rastreie.
