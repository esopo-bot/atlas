# Como trabalhar no atlas — leia antes de agir

Prompt de abertura para sessão que vai MELHORAR a camada (o alvo é o
próprio atlas). Cole inteiro e escreva o pedido no fim. A sessão de
projeto, em que o atlas orquestra e o alvo é outro repositório, usa o
prompt 03, vizinho deste.

## As cinco leis do atlas

1. **Só é pronto o que um instrumento provou.** Prova é comando com saída
   vista, e a saída se COLA do terminal — nunca se redige de memória.
2. **Todo caso novo nasce vermelho**: quebre só a linha de decisão, veja
   falhar, conserte, veja passar.
3. **Edite a fonte, nunca a cópia.** Depois: `python3 montar.py
   --sincronizar` e prove com `--verificar`. Fontes: `modulos/<nome>/` para
   os módulos, `.agents/skills/` para skills, `nucleo/*.json` para regras e
   dados. `conhecimento/mapa-do-repositorio.md` diz onde cada coisa mora.
4. **Mudança na camada passa pela skill `portao`**: dispare-a antes de
   escrever, e diga em que barreira cada parte do pedido bate. Publicar é
   do dono, sempre — o teto da sessão é o ensaio.
5. **Commit e push são seus, na branch de trabalho; a mescla é na branch
   de integração** (a que `nucleo/executor.json` declara). A branch de
   publicação e a publicação são do dono. Se o harness negar o `git push`,
   não brigue: use clone local como origin e avise o dono no fim.

## Como falar com o dono

- Ele não programa. Seja claro, não longo: frase curta, uma ideia por
  parágrafo, negrito só no que decide.
- Pergunta: uma por vez, no máximo 3 opções, com recomendação e o porquê
  em uma linha.
- Issue e comentário: escreva como a conta de automação declarada em
  `issues.conta_gh` do `nucleo/executor.json` (a técnica de token por
  ambiente está no `caixa.py`); se não conseguir, prefixe a mensagem com
  o nome dela — nunca deixe parecer que o dono escreveu.
- Registre o andamento NA issue do trabalho: o corpo dela é o único
  contexto que sobrevive entre sessões. Issue contém somente a VERDADE,
  checada no repositório — corpo desatualizado mente para a próxima
  sessão; atualize a cada marco, não no fim.

## A receita do executor de roteiros — pedágios já pagos

- Copie `execucoes/entrega.json` para nome local com `auditoria: true` e
  `issue: <n>`. Não edite o original.
- Árvore descartável: clone local (`git clone --no-hardlinks . /tmp/issue-<n>`).
  O `nucleo/executor.json` vai para `nucleo/` DA ÁRVORE — nunca para a
  raiz. Copie também o `.mcp.json`. Arquivo local (fora do git) não viaja
  no clone: o que a execução consertar nele, porte para a raiz com grep de
  prova.
- Dispare DA RAIZ, com `ISSUE=<n> ASSUNTO=<kebab>` no ambiente — sem eles
  a branch nasce errada. `ensaio` antes de `executar`. Motor e retomadas
  SEMPRE desacoplados (`nohup ... &`) — matar o motor no meio deixa estado
  órfão.
- Arme um vigia em background no `estado.json` do trabalho: motor parou →
  auditar NA HORA. `aguardando-resposta` significa processo MORTO
  esperando decisão: tocar o arquivo de aprovação sozinho não retoma —
  relance com `--retomar`.
- Ao parar: rode o auditor à mão
  (`python3 .agents/auditor/auditor.py execucoes/evidencias/issue-<n> --cwd /tmp/issue-<n>`),
  sem `PROJETO` na frente — a execução gravou o ambiente em `ambiente.json`,
  ao lado do `estado.json`, e o auditor o repõe ao re-executar; a variável no
  shell é IGNORADA onde esse arquivo existe, e quem quiser apontar as provas a
  outro alvo edita o `ambiente.json` da pasta. Confira a substância, só então aprove
  (`touch <árvore>/aprovacoes/entrega.ok`) e retome com `--retomar`.
- A branch de trabalho JÁ ESTÁ aqui quando você vai integrar: a etapa
  `trabalho-empurrado` a empurrou da árvore descartável assim que o commit
  existiu, e provou com `git ls-remote`. Não busque à mão — confira com
  `git rev-parse <branch>` e mescle `--no-ff` na integração + push. Rode o
  ritual DEPOIS da mescla — texto novo pode acordar a rotina de vocabulário.
  Depois: critérios com saída colada na issue, feche-a, pode a linha da caixa
  com o commit, apague a branch entregue.
- A sessão do motor que gastar o teto sem commitar declara `segue` vazio
  e a retomada a pula: preserve a trilha, dê mapa no Ponto de retomada da
  issue (arquivos, ordem, "commite cedo") e recomece a execução.

## Antes de abrir trabalho novo

`git status --short && python3 verificacoes.py ritual` — árvore suja ou
ritual vermelho (fora a rotina `entrega`, que fecha com a mescla na
integração): pare e avise.

## Ao fechar o dia

Esfriamento pela skill `esfriamento`; relatório do que a rodada provou e
acusou como comentário na issue fixa do quadro; varredura final ZERADA —
nenhum motor vivo, nenhuma aprovação pendente, nenhuma issue sem próximo
passo escrito, nenhuma branch entregue por apagar.

---

## O PEDIDO

<escreva aqui o pedido desta sessão: o que muda no mundo quando fechar,
o que está fora, e onde mora a decisão que você já tomou>
