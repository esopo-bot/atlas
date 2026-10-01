---
name: busca-de-codigo-existente
description: Busca de código já existente antes de escrever código novo. Use antes de criar serviço, helper, contrato, componente, endpoint, funcionalidade ou aplicação do zero. Procura nos repositórios do workspace e cita o que achou, com caminho e linha, antes da primeira linha nova. Escopo — CÓDIGO. Perfil de repositório é da perfil-de-repositorio; documentação é da documentar-processo; issue é da trabalho-por-issue. Palavras que a acordam — "já existe algo assim?", "tem componente parecido?".
context: fork
agent: Explore
background: false
---

# Antes de criar

Código novo nasce depois de procurar o que já existe nos repositórios
vizinhos e citar o que achou: procurar → citar → só então criar.

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

## Quando roda à parte

No Claude Code, esta skill roda num subagente, sem a conversa de quem pediu.
O pedido chega no fim, na linha `ARGUMENTS:`, e tem de trazer o conceito a
procurar — o que a peça nova faria, nas palavras que o código usaria — e a
linguagem, quando quem pede sabe. Sem conceito, devolva numa linha o que
faltou; não adivinhe. Devolva a frase do passo 3 e, se houver, o perfil do
repositório mais parecido: quem cria é quem pediu, e o passo 4 é dele.
