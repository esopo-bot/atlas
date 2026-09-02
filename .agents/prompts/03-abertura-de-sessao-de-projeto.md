# Sessão de PROJETO — o atlas orquestra, o alvo é outro repositório

Prompt de abertura para sessão que trabalha num repositório vizinho pelo
executor de roteiros da camada. Cole inteiro e escreva o pedido no fim.
Melhoria da própria camada é do prompt 01, vizinho deste — os dois nunca
se misturam.

## A barreira que manda em tudo

Você NÃO muda a camada no meio de trabalho de projeto. Achado de melhoria
do atlas vira LINHA no quadro fixo (`python3 .agents/caixa/caixa.py
melhoria --id <kebab> --assunto "..."`), nunca edição. O auditor fica
LIGADO em toda execução: é ele quem colhe o que melhora a camada depois.

Conhecimento de projeto é LOCAL: nasce no espaço do workspace, nunca nas
páginas da camada. Nome de empresa, conta e caminho de máquina não entram
em nada que a camada rastreie.

## Sessões paralelas — uma por território

Várias sessões podem trabalhar ao mesmo tempo, e o que separa uma da outra
é o território, não o assunto:

- **Cada sessão escreve só no seu alvo** — o repositório declarado em
  `PROJETO`. Pasta de outro projeto é de outra sessão, mesmo que o pedido
  pareça o mesmo: duas sessões receberam a mesma tarefa em 01/09 e só não
  colidiram porque uma olhou a pasta antes de escrever.
- **A camada é intocável para todas.** Achado vai ao quadro pelo
  instrumento; edição do atlas é de sessão própria, pelo prompt 01.
- **O estado de cada sessão mora na issue dela.** Nada de arquivo
  compartilhado de andamento: a issue é o único lugar que a outra sessão e
  a próxima leem.
- **Antes de escrever numa pasta, olhe quem a tocou.** `ls -lt` da pasta
  alvo e `git -C <alvo> status --short`: mudança recente que você não fez é
  outra sessão viva — não commite nem apague o que não é seu.

## As cinco leis (valem aqui também)

1. Só é pronto o que um instrumento provou — saída COLADA do terminal.
2. Todo caso novo nasce vermelho: veja falhar, conserte, veja passar.
3. Edite a fonte, nunca a cópia (no projeto: nada de editar build ou
   arquivo gerado).
4. Achado de camada vai ao quadro pelo instrumento — não se edita o atlas.
5. Commit e push são seus na branch de trabalho do ALVO; a mescla na
   integração do alvo é da rodada, DEPOIS da auditoria; a branch de
   publicação do alvo é do dono, sempre.

## O fluxo

1. História = issue no repositório que `issues.repositorio` do
   `nucleo/executor.json` declara, com a etiqueta que a chave `projetos`
   dá ao alvo. O pedido refinado mora nela.
2. Leia antes o conhecimento local do workspace sobre o alvo — não
   redescubra o que já foi medido.
3. Território: só se escreve no alvo declarado em `PROJETO`. Repositório
   com `somente_leitura: true` em `projetos.<etiqueta>` do
   `nucleo/executor.json` é leitura e investigação — o caminho lá é
   sugestão com o dono do território como revisor. Essa é a única
   lista: o gancho de veto deriva dela. Erro causado por sistema de
   terceiro: PARE e avise.
4. Branch de trabalho nasce da integração do alvo. Implemente com teste
   vermelho antes; rode a suíte do alvo.
5. Entrega da rodada: mescla `--no-ff` na integração do alvo + push (a
   automação do alvo valida) + pedido de incorporação da integração para
   a branch de publicação, na conta que o fluxo do alvo pedir, sempre
   deixando claro o que é trabalho de agente. Quem mescla a publicação é
   o dono. Só trabalho auditado entra.
6. Entregue e **pode o rastro**: a branch de trabalho já contida na
   branch de incorporação não fica de pé, nem local nem remota — a poda
   remota é a que se esquece, e é a que todo mundo vê. Quem acusa é
   `python .agents/camada/camada.py --entrega`; guardar uma delas é
   declará-la em `.claude/branches-protegidas.txt`.
7. Registre o andamento NA issue; critérios com saída colada. **Não
   existe arquivo de andamento** — nem `andamento.md`, nem
   `onde-parei.md`. Arquivo assim vira uma segunda verdade que ninguém
   atualiza junto, e é ele que a próxima sessão lê. O `.md` só entra no
   ENCERRAMENTO, para extrair o que vale adiante, e nasce em
   `conhecimento/`. Quem cobra é o gancho `vetar-andamento-em-arquivo`.

## A receita do executor de roteiros para vizinho

- Roteiro local a partir do roteiro de vizinho do seu catálogo (o
  `execucoes/LEIAME.md` lista os roteiros; se o de vizinho ainda for
  local, peça-o ao dono), com `auditoria: true` e `issue: <n>`. Não
  edite o original.
- Disparo DA RAIZ do workspace:
  `PROJETO=projetos/<nome> ISSUE=<n> ASSUNTO=<kebab> nohup python3
  .agents/encadeador/encadeador.py executar --roteiro <local>
  --trabalho issue-<n> --dir execucoes/evidencias &` — `ensaio` antes;
  vigia em background no `estado.json`.
- Ao parar: auditor à mão, sem `PROJETO` na frente — a execução gravou o
  ambiente em `ambiente.json`, ao lado do `estado.json`, e o auditor o repõe
  ao re-executar; a variável no shell é IGNORADA onde esse arquivo existe.
  Para apontar as provas a outro alvo, edite o `ambiente.json` da pasta, não
  o shell. Substância verificada, aí retome com `--retomar`.
- A verificação cobra os critérios ABERTOS da issue inteira: se a issue
  tem blocos fora do escopo desta execução, escreva na issue o que fecha
  e o que fica, antes de retomar.

---

## O PEDIDO

<escreva aqui o pedido desta sessão: o alvo, o que muda nele quando
fechar, o que está fora, e a prioridade se houver mais de um bloco>
