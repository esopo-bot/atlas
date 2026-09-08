---
description: Bootstrap de abertura de sessão para o atlas no Codex (sem slash command).
---

# Bootstart do Atlas para Codex — manual de bordo de entrada (versão mecânica)

Objetivo deste arquivo: trazer contexto suficiente para iniciar sem adivinhação, reduzir retrabalho, e padronizar o formato do turno. O método é gastar mais contexto no começo para diminuir erros e correções depois.

## 0) PROTOCOLO DE TURNO OBRIGATÓRIO (copiar para o início da resposta)

Em qualquer sessão nova ou retomada de tarefa no Atlas, antes de agir, a abertura do turno deve seguir nesta ordem fixa:

1. Definir o fluxo.
2. Ler trilha obrigatória completa.
3. Separar fonte/cópia/local.
4. Rodar saúde mínima.
5. Rodar indexação inicial.
6. Montar pedido técnico padronizado.
7. Só então executar mudanças.

### 0.1 Checklist de abertura (marcar no início do turno)

- [ ] Fluxo escolhido (camada/projeto vizinho) identificado.
- [ ] Leituras obrigatórias feitas na ordem definida.
- [ ] Regra de fonte/cópia/local aplicada.
- [ ] Comandos de saúde executados.
- [ ] Comandos de indexação inicial executados.
- [ ] Riscos e decisões de ambiguidade mapeados.
- [ ] Bloco de pedido final preenchido.

### 0.2 Formato obrigatório da mensagem de abertura (pré-turno)

A sessão deve responder no bloco abaixo no início de cada turno de trabalho:

```text
ABERTURA DE TURNO (protocolo Atlas)
- Fluxo: <camada | projeto vizinho>
- Motivo do turno: <resumo do que vamos fazer agora>
- Hipótese operacional: <hipótese inicial do que pode estar errado/necessário>
- Suposições aceitas: <lista curta do que está sendo assumido>
- Escopo: <o que muda e o que não muda>
- Riscos: <1) risco técnico, 2) risco de contexto, 3) risco de regra>
- Decisão do dono necessária: <sim/não + o que falta>
- Estado de comando/teto: <estado atual de contexto e limites de tempo/custo>
```

Se algum item ficar vazio, a sessão deve pedir ajuste antes de executar.

## 1) Alavanca 1 — escolha do fluxo (obrigatória)

### Definição

- **Fluxo da Camada**: alvo é o próprio atlas (`AGENTS.md`, `conhecimento/`, `nucleo/`, `modulos/`, `execucoes/`, `.agents/*`).
  - Próximo prompt: `01-abertura-de-sessao-na-camada.md`
- **Fluxo de Projeto Vizinhos**: alvo é `projetos/<nome>` ou outro repositório orquestrado pelo atlas.
  - Próximo prompt: `03-abertura-de-sessao-de-projeto.md`

### Regra

- Em dúvida entre os dois, usar **Fluxo da Camada**.
- Registrar decisão curta no `ABERTURA DE TURNO`.
- Em fluxo vizinho, é proibido mudar regras, fonte ou skill no atlas. Use o quadro de melhorias da camada no momento certo.

## 2) Alavanca 2 — trilha de leitura obrigatória (ordem fixa)

1. `AGENTS.md`
2. `conhecimento/regras-da-camada.md`
3. `conhecimento/mapa-do-repositorio.md`
4. `conhecimento/LEIAME.md`
5. `protocolo do fluxo escolhido` (`01...` ou `03...`) inteiro

### Validação da trilha

- Sem essa ordem, considerar que abertura está incompleta.
- Não inferir regra nova; buscar origem em texto oficial de arquivo.

## 3) Alavanca 3 — modelo mental de onde editar e onde só ler

### Fontes (editar aqui)

- `.agents/` (skills, prompts, ganchos, roteiros, instrumentos)
- `nucleo/` (definições da camada)
- `modulos/` (peças de módulo)
- `conhecimento/` (páginas de conhecimento)
- `AGENTS.md` e `README.md` quando aplicável

### Cópias (não editar como origem)

- `.claude/` (derivação operacional)
- `execucoes/` quando gerado como saída de execução local
- arquivos produzidos por `montar.py` sem vínculo de origem no diretório editado

### Estado local (não entra como entrega)

- `.agents/indice/alvos.json`
- `.agents/indice/ultima-ronda.json`
- `.claude/settings.local.json`
- `tmp/`, arquivos temporários e logs de sessão

### Regra de ouro

- Se houver incerteza, não editar. Confirmar primeiro se o caminho é origem, cópia ou estado local.

## 4) Alavanca 4 — regras de operação (comportamento não negociável)

- Só declarar pronto com prova de execução.
- Antes de criar ou alterar, procurar e citar evidência no repositório.
- Decisões de impacto exigem pedido explícito de validação com risco e consequência.
- Mudança destrutiva ou branch/CI de integração exige decisão explícita do dono.
- Segredos em texto rastreado não entram; usar `${VARIAVEL}`.
- Na camada genérica, acionar skill `portao` antes da primeira alteração.
- Em saída, explicar para leitura de nível júnior primeiro.
- Fechar cada resposta de abertura com **Conclusão primeiro** e frases curtas.

## 5) Alavanca 5 — checagem de saúde da camada (pré-requisito)

Executar em abertura:

1. `python .agents/camada/camada.py medir provar`
2. `python verificacoes.py ritual`
3. `python .agents/camada/camada.py --matricula` (quando mexer em instrumentos)
4. `python .agents/indice/indexar.py --estado`
5. `python .agents/camada/camada.py --quadro` (onde a issue nasce — procurar no repositório de código devolve zero, e zero parece resposta)

### Regra de falha

- Qualquer falha bloqueia execução prática.
- Registrar erro e hipótese de causa; só prosseguir com alinhamento.

## 6) Alavanca 6 — indexação de entrada (para não adivinhar)

### O que indexar primeiro

- `.agents/indice/alvos.json`: configuração e escopos de busca
- `.agents/indice/ultima-ronda.json`: estado da última ronda
- `indexar.py`: atualiza índice operacional
- `buscar.py`: consulta no índice

### Sequência obrigatória de entrada

1. `python .agents/indice/indexar.py --estado`
2. `python .agents/indice/indexar.py --ensaio`
3. `python .agents/indice/indexar.py --ronda` *(ou sem flag, quando necessário)*
4. `python .agents/indice/buscar.py "<pergunta>" --alvo conhecimento --quantos 5`

### Regras de consulta e decisão

- Prefira `--alvo` para reduzir ruído.
- Resultado vazio de alvo não indexado = configuração incompleta, não ausência de evidência.
- Se o índice divergir da trilha de leitura, priorizar fonte original e sincronizar com `montar.py --sincronizar` quando fizer sentido.

## 7) Alavanca 7 — risco, contexto e teto de saída

- Registrar hipótese e decisão já no início do turno.
- Não tomar decisão implícita; explicitar escolha e alternativa.
- Antes de partir para código, checar risco de contexto:
  - o que pode quebrar regra
  - o que pode ampliar escopo indevidamente
  - o que pode ficar sem prova
- Bloquear se houver risco estrutural sem critério de rollback.

## 8) Alavanca 8 — plano padrão de resposta de cada turno (formato fixo)

Preencher na resposta em ordem fixa:

1. **Status de abertura:** fluxo, leituras concluídas, saúde, indexação.
2. **Objetivo do dono:** objetivo explícito e limite de escopo.
3. **Decisão tomada:** decisão explícita + decisão pendente.
4. **Plano de execução:** passos, ordem e ponto de validação.
5. **Plano de validação:** como provar cada passo.
6. **Riscos e contenção:** risco, impacto e rollback.
7. **Bloco de pedido:** campos obrigatórios da seção seguinte.

### 8.1 Protocolo de fala e perguntas

- Frase curta com uma ideia por linha.
- Negrito só em decisão, risco alto ou ponto de bloqueio.
- Sempre em `pt-BR`.
- Perguntas ao dono:
  - fazer **uma por vez**;
  - formato recomendado:
    1) Pergunta: `<o que precisa decidir>`.
    2) Recomendação: `<opção sugerida>`.
    3) Por quê: `<impacto e risco se não decidir>`.
  - incluir link/identificador quando houver PR, issue, comentário, página ou evidência.
- Se houver risco operacional novo, alertar mesmo se o dono já tiver recusado a ideia anterior.
  O alerta deve dizer o que mudou para não repetir erro.

## 9) Alavanca 9 — comunicação de progresso e riscos (sem ruído, sem adivinhação)

- Prioridade de mensagem em cada retorno:
  1. **Conclusão de estado atual** (1 linha).
  2. **Provas executadas** (comando + saída).
  3. **Risco mais relevante**.
  4. **Próximo passo mínimo**.
- Se houver decisão pendente, incluir:
  - o que foi testado,
  - por que ainda não segue,
  - o que falta do dono.
- Regra de economia de turno: evitar repetições sem mudança de estado.

## 10) Fechamento da abertura e início do trabalho

Somente após os blocos anteriores completos:

- Ler `execucoes/LEIAME.md` quando houver roteiro do executor.
- Repassar prompt de fluxo escolhido integralmente.
- Iniciar trabalho no alvo correto com comando mínimo necessário.
- No fluxo de projeto vizinho, manter isolamento do alvo e registrar tudo na issue do alvo.

## 11) O PEDIDO (preencher ao abrir)

- **Fluxo escolhido:** Camada / Projeto Vizinhos
- **Escopo em resultado:** o que muda ao fechar
- **Fora de escopo:** o que fica explícito sem mexer
- **Decisões do dono:** pontos que exigem resposta
- **Plano de validação:** como provar cada passo
- **Prioridade operacional:** ordem de execução
- **Risco de contexto/execução:** pontos sensíveis e contenção
- **Conflitos entre fontes:** regra de resolução sem suposição
