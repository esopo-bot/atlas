# A camada foi atualizada — verifique e limpe antes de trabalhar

Prompt para o repositório que INSTALA o atlas. Cole numa sessão aberta na
raiz do repositório logo depois de uma atualização da camada (o
`montar.py` novo já rodou aqui). O objetivo: provar que a instalação está
íntegra e que nada da versão anterior ficou para trás.

## O que aconteceu

A camada instalada neste repositório foi atualizada e
`python3 montar.py --sincronizar` já foi executado. Atualização regrava
as cópias — nunca se edita cópia à mão — mas ela não remove sozinha o que
a versão nova deixou de escrever: skill renomeada, gancho aposentado,
página movida. Isso é a sujeira que esta sessão caça.

## O checklist

Marque cada linha só depois de colar a saída que a prova. Linha sem saída
colada não está feita.

### 1. O que mudou desta versão para a anterior

- [ ] **A versão que chegou:** `grep -m1 '^VERSAO' montar.py`.
- [ ] **A versão que estava aqui antes:**
      `git log -1 --format=%H -- montar.py` e, com esse SHA,
      `git show <SHA>^:montar.py | grep -m1 '^VERSAO'`. Se o repositório
      não rastreia o `montar.py`, diga isso e pule — não invente o número.
- [ ] **O diff da atualização:** `git diff --stat HEAD~1 -- .agents .claude
      conhecimento nucleo montar.py`, ou, se a atualização ainda não foi
      commitada, `git status --short`. Leia a lista inteira e agrupe em três
      colunas: **entrou**, **mudou**, **saiu**. É a coluna "saiu" que gera a
      sujeira dos passos seguintes.
- [ ] **O que o dono precisa saber:** três a cinco linhas sobre o que a
      versão nova muda no trabalho DELE — instrumento novo, bandeira nova,
      passo que deixou de existir. Nunca a lista de arquivos.

### 2. A instalação está íntegra

- [ ] **A carga bate com o disco:** `python3 montar.py --verificar` — tem de
      sair zero. Divergência aqui é cópia editada à mão ou atualização pela
      metade: pare e mostre ao dono antes de qualquer outra coisa.
- [ ] **Os instrumentos respondem:** rode o `--testar` de cada instrumento
      de `.agents/` (todo instrumento da camada tem o seu). Um vermelho aqui
      é defeito de instalação, não do seu repositório. **Cuidado com dois:**
      o `gatilho` abre sessões de verdade e cobra por elas — só rode se o
      dono pedir; e o do `encadeador` demora minutos.
- [ ] **O ritual, se este repositório o tiver:** `python3 verificacoes.py
      ritual`. Ele só existe no repositório da camada; ausente aqui, não é
      falha.

### 3. O que a versão nova precisa e talvez não esteja instalado

Confira **só o que este repositório usa**. Ferramenta que ninguém aqui
chama não precisa existir — e instalar por precaução é sujeira futura.

- [ ] `python3 --version` e `git --version` respondem. São o piso; sem eles
      nada da camada roda.
- [ ] `gh auth status` — necessário se o repositório abre issue, comenta ou
      mexe no quadro. Se a camada aqui move cartão de projeto, a linha de
      escopos precisa trazer `project`; só `repo` comenta e etiqueta, mas
      nunca move. A saída para o que falta é `gh auth refresh -s project`.
- [ ] `claude --version` — necessário só se o executor de roteiros roda
      aqui.
- [ ] Módulo instalado que pede serviço de fora (o `indice` pede banco
      vetorial e servidor de modelo) — abra o `LEIAME.md` do módulo em
      `.agents/<modulo>/` e siga a receita DELE. Não escreva receita nova:
      se a de lá não funciona neste ambiente, isso é achado para o dono,
      não conserto seu.
- [ ] **Ambiente corporativo trancado** (proxy que reassina TLS, registro de
      pacote bloqueado, política que barra CLI): não contorne. Registre o
      que travou, com a mensagem de erro exata, e devolva ao dono.

### 4. A sujeira que a versão anterior deixou

- [ ] **Liste antes de apagar:** `python3 .agents/limpeza/limpeza.py rodar
      --workspace .` — sem `--aplicar` ele só LISTA. Leia a lista e separe
      em duas: o que é resto da camada antiga (candidato a sair) e o que é
      arquivo seu que só parece órfão (fica).
- [ ] **Cruze com a coluna "saiu"** do passo 1: arquivo que a versão nova
      deixou de escrever e continua no disco é resto, e é o caso mais comum
      — skill renomeada, gancho aposentado, página movida.
- [ ] **Aplique só o que você separou:** `--aplicar`. O que restar de
      dúvida, **pergunte ao dono antes**: remover é destrutivo, e
      destrutivo é do dono. Nunca apague fora da lista do instrumento.
- [ ] **Referência quebrada:** procure no repositório citações aos caminhos
      que sumiram (grep pelos nomes da coluna "saiu"). Corrija só apontador
      para a camada, nunca conteúdo seu.

### 5. O relato

- [ ] O que mudou de versão para versão, em linguagem de quem usa.
- [ ] O que foi verificado, com as saídas coladas.
- [ ] O que saiu, o que ficou por decisão e o que ficou por dúvida. **Sem
      lista de removidos não houve limpeza — houve fé.**
- [ ] O que travou e é do dono resolver, com a mensagem de erro exata.

## O par de settings: o que é da camada e o que é seu

O Claude Code lê DOIS arquivos em `.claude/`, e a atualização trata cada
um de um jeito:

- **`settings.json`** é DA CAMADA: rastreado, viaja, e a atualização o
  regrava. Nunca edite — edição aqui morre na próxima atualização, e
  valor pessoal aqui vaza para o git.
- **`settings.local.json`** é SEU: fora do git, sobrevive a toda
  atualização. É o lugar certo de tudo que é desta máquina e desta
  pessoa: permissões liberadas (`permissions.allow`), servidores MCP
  habilitados (`enabledMcpjsonServers`), ganchos pessoais (`hooks`),
  variáveis de ambiente. Os dois se somam na leitura; o local acrescenta
  sem tocar no da camada.

Depois de atualizar, faça a triagem dos valores:

1. Abra os dois e compare. Valor PESSOAL que esteja no `settings.json`
   (permissão da sua máquina, gancho seu, caminho local) está no lugar
   errado: leve-o para o `settings.local.json` — a atualização não o
   levaria, e a próxima o apagaria.
2. Procure valor perdido: permissão que você tinha e sumiu, servidor MCP
   que parou de aparecer, gancho pessoal que deixou de disparar — tudo
   isso se recoloca no `settings.local.json`, nunca no da camada.
3. Segredo não entra em NENHUM dos dois por valor: em arquivo rastreado
   vai `${VARIAVEL}`; no local, prefira apontar para onde a credencial
   mora a colar o valor.
4. Prove que o resultado é legível:
   `python3 -m json.tool .claude/settings.local.json > /dev/null && echo legivel`
   — e lembre que gancho novo só carrega em sessão nova.

## O que esta sessão NÃO faz

Não edita cópia da camada (regra: fonte, nunca cópia — e a fonte mora no
repositório da camada, não aqui). Não apaga nada fora da lista do
instrumento sem perguntar. Não commita sem o repositório autorizar em
`nucleo/configuracao.json`, campo `autorizacoes` — omissão não é
permissão.
