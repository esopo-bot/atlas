# A camada foi atualizada — verifique e limpe antes de trabalhar

Receita para o repositório que INSTALA a camada, numa sessão aberta na raiz
logo depois de `python <pasta do clone do atlas>/montar.py --atualizar`.
Atualização regrava as cópias, mas não remove o que a versão nova deixou de
escrever: skill renomeada, gancho aposentado, página movida. O que a camada
instalou está em `.agents/camada/registro-da-instalacao.json`. Marque cada
linha só com a saída colada.

## 1. O que mudou

- [ ] A versão que chegou: `commit_da_camada` do registro.
- [ ] A que estava antes: `git log -1 --format=%H -- .agents/camada/registro-da-instalacao.json`
      e `git show <SHA>^:.agents/camada/registro-da-instalacao.json`. Sem
      registro rastreado, diga isso e pule.
- [ ] O diff: `git diff --stat HEAD~1 -- .agents .claude conhecimento nucleo`
      (ou `git status --short` se não commitou). Agrupe em entrou, mudou,
      saiu: a coluna "saiu" gera a sujeira do passo 3.
- [ ] Três a cinco linhas ao dono sobre o que muda no trabalho dele; nunca
      a lista de arquivos.

## 2. A instalação está íntegra

- [ ] `python <pasta do clone do atlas>/montar.py --verificar` sai zero;
      divergência é cópia editada à mão ou atualização pela metade: pare e
      mostre ao dono.
- [ ] Um `montar.py` antigo na raiz daqui não é mais a origem; apagar é do
      dono.
- [ ] O `--testar` de cada instrumento de `.agents/` passa. Cuidado: o
      `gatilho` abre sessões pagas (só com o dono); o `encadeador` demora
      minutos; o `buscar.py` sem banco se declara "não medido".
- [ ] `python verificacoes.py ritual`, se existir aqui (só existe no
      repositório da camada).
- [ ] O que a versão nova precisa: um Python 3 que responda
      (`python -c "import sys; print(sys.version_info[0])"`; no Windows
      `python3` é o atalho da loja e engana o `which`), `git --version`,
      `gh auth status` (escopo `project` se a camada move cartão), `claude
      --version` se o executor roda aqui, e a receita do módulo que pede
      serviço de fora (a do `indice` é `conhecimento/indice.md`). Ambiente
      trancado não se contorna: registre a mensagem exata ao dono.

## 3. A sujeira que a versão anterior deixou

- [ ] `python .agents/limpeza/limpeza.py rodar --workspace .` lista sem
      apagar; separe resto da camada antiga de arquivo seu que só parece
      órfão.
- [ ] Cruze com a coluna "saiu" do passo 1.
- [ ] `--aplicar` só no que você separou; dúvida é pergunta ao dono, porque
      destrutivo é dele. Nunca apague fora da lista do instrumento.
- [ ] Referência quebrada: `grep` pelos nomes da coluna "saiu"; corrija só
      apontador para a camada.

## 4. O relato

O que mudou de versão para versão em linguagem de quem usa; o que foi
verificado, com saída; o que saiu, o que ficou por decisão e por dúvida
(sem lista de removidos não houve limpeza); o que travou e é do dono.

## O par de settings

`.claude/settings.json` é da camada: rastreado, regravado na atualização,
nunca editado. `.claude/settings.local.json` é seu: fora do git, sobrevive,
e guarda o que é desta máquina (`permissions.allow`,
`enabledMcpjsonServers`, ganchos pessoais, variáveis). Depois de atualizar,
leve valor pessoal que esteja no da camada para o local, reponha no local o
que sumiu, e prove:
`python -m json.tool .claude/settings.local.json > /dev/null && echo legivel`.
Segredo não entra em nenhum dos dois por valor. Gancho novo só carrega em
sessão nova.

Esta sessão não edita cópia da camada, não apaga fora da lista do
instrumento sem perguntar, e não commita sem `autorizacoes` em
`nucleo/configuracao.json`.
