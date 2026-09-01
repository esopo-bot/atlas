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
6. Registre o andamento NA issue; critérios com saída colada.

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
