---
name: antes-de-criar
description: Antes de criar serviço, helper, contrato, componente ou funcionalidade nova, procure o que já existe nos repositórios do workspace e cite o que achou. Use sempre que a tarefa envolver criar ou implementar algo novo, começar uma aplicação do zero, ou quando pedirem para verificar se algo já existe no conjunto.
---

# Antes de criar

O padrão natural do agente é duplicar o que já existe num repositório
vizinho. Esta skill o troca por procurar → citar → só então criar.

## O fluxo

1. **Consulte a wiki.** O mapa em `conhecimento/projetos/LEIAME.md` diz o que
   cada repositório oferece; o perfil do repositório alvo e dos vizinhos diz
   onde está e que padrões seguir. Sem wiki no workspace, diga isso e sugira
   gerá-la (skill `wiki-de-projetos`).
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
