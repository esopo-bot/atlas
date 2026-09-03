---
name: busca-de-codigo-existente
description: Busca de código já existente antes de escrever código novo. Use antes de criar serviço, helper, contrato, componente, endpoint, funcionalidade ou aplicação do zero. Procura nos repositórios do workspace e cita o que achou, com caminho e linha, antes da primeira linha nova. Escopo — CÓDIGO. Perfil de repositório é da perfil-de-repositorio; documentação é da documentar-processo; issue é da trabalho-por-issue. Palavras que a acordam — "já existe algo assim?", "tem componente parecido?".
---

# Antes de criar

O padrão natural do agente é duplicar o que já existe num repositório
vizinho. Esta skill o troca por procurar → citar → só então criar.

## O fluxo

1. **Liste o que está clonado, depois consulte a wiki.** A lista do que
   existe é a pasta dos repositórios (`ls projetos/`, ou a que o workspace
   usar) — a wiki em `conhecimento/projetos/LEIAME.md` é o perfil destilado
   de cada um, e pode estar atrasada: repositório sem perfil ainda existe.
   Nunca conclua "não está clonado" pela wiki; conclua pela pasta. Sem wiki
   no workspace, diga isso e sugira gerá-la (skill `perfil-de-repositorio`).
2. **Busque na hora.** A wiki é destilada; o código é a verdade. Procure o
   conceito nos repositórios antes de concluir que não existe:

   ```bash
   grep -ri "<conceito>" <pasta dos repositórios> --include="*.<ext>" -l
   ```

   Com acesso à organização no GitHub (MCP), busque também lá: o conjunto do
   trabalho é maior que o disco local.
3. **Cite antes de criar.** Uma das duas frases, sempre:
   - "Já existe: `<repositório/caminho>` — vou reusar/estender."
   - "Não existe: procurei `<termos>` na wiki, no grep e em `<onde mais>`."

   Sem citação, não crie. Achado reusável vence implementação nova.
4. **Criando, imite os repositórios vizinhos.** Aplicação ou módulo novo
   segue os padrões do perfil do repositório mais parecido — stack,
   organização de pastas, convenções de nome, jeito de testar. Parecido por
   fora, parecido por dentro.

## O corte

Reuso tem limite: se estender o que existe custar mais que criar limpo, crie —
mas diga o porquê, citando o que descartou. O proibido não é criar; é criar
sem ter procurado.

## Pedidos de exemplo

- "vou precisar de um helper pra formatar CPF, dá uma olhada se já não existe isso em algum lugar antes de eu escrever"
- "quero começar uma aplicação nova pra controlar as escalas do plantão. antes de eu criar do zero, tem algo parecido no workspace?"
- "preciso de um serviço de envio de e-mail. já tem algo assim nos nossos repositórios?"
