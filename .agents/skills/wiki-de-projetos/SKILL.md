---
name: wiki-de-projetos
description: Gera e atualiza a wiki local dos repositórios do workspace de forma incremental - consulta o índice antes de varrer, pula o que não mudou pelo SHA do git, tipa cada repositório (api, ui, infraestrutura...) e escreve o perfil na profundidade certa, poucos por rodada. Use quando pedirem para indexar os projetos, gerar ou atualizar a wiki, criar o perfil de um repositório, ou depois de mudança grande num projeto.
---

# Wiki de projetos

A wiki impede o agente de inventar o que já existe: um perfil destilado por
repositório e um mapa do conjunto, em `conhecimento/projetos/`. Ela é
**incremental por lei**: o índice diz o que mudou, e só o que mudou é lido.

## As três leis

1. **Consulte o índice antes de abrir qualquer repositório.** O estado mora
   em `conhecimento/projetos/indice.json`. Não existe? Crie na primeira
   rodada.
2. **Um repositório por vez.** Leia, destile, escreva o perfil no disco e só
   então passe ao próximo. O disco é a memória — nunca segure dois
   repositórios no contexto: há sessões com janela pequena, e o que não foi
   escrito evapora.
3. **Poucos por rodada.** No máximo 3 perfis completos por execução. O resto
   fica `"pendente": true` no índice e abre a rodada seguinte — a dívida é
   explícita, nunca esquecida.

## O índice

`conhecimento/projetos/indice.json` — estado para máquina; prosa fica nos
perfis. O template atual é a versão 2. Uma entrada por repositório:

```json
{
  "versao_do_template": 2,
  "repositorios": {
    "nome-do-repo": {
      "sha_indexado": "a1b2c3d",
      "data": "2026-08-05",
      "tipo": "infraestrutura",
      "tipo_declarado_pelo_dono": false,
      "arquivos_chave": ["README.md", "variables.tf", "outputs.tf"],
      "versao_do_template": 2,
      "pendente": false
    }
  }
}
```

## A rodada, passo a passo

1. Leia o índice.
2. **Triagem barata, sem abrir arquivo** — para cada repositório da pasta:
   `git -C <repo> rev-parse --short HEAD` e compare:
   - SHA igual e `versao_do_template` atual → **pula**.
   - SHA mudou, mas `git -C <repo> diff --name-only <sha_indexado>..HEAD --
     <arquivos_chave>` vem vazio → **leve**: atualize SHA e data no índice;
     perfil intocado. Leve não conta no teto.
   - Diff toca arquivo-chave, repositório novo, ou `versao_do_template`
     antiga → **perfilar** (conta no teto de 3).
3. **Relate a triagem antes de varrer** — "N em dia, N leves, N a perfilar,
   N pendentes para a próxima rodada" — e só então trabalhe.
4. Para cada um do lote, nesta ordem: **tipe** e **perfile** na profundidade
   do tipo — leia `references/tipos-de-perfil.md` para os sinais, os
   templates e os arquivos-chave de cada tipo. Escreveu o perfil, atualize a
   entrada no índice e esqueça o repositório.
5. Regenere o mapa (`LEIAME.md`, 1–3 linhas por repositório) e deixe tudo na
   régua: `npx --yes markdownlint-cli2 --fix "conhecimento/projetos/*.md"`.

## Regras que não mudam

- Tipo declarado pelo dono (`tipo_declarado_pelo_dono: true`) nunca é
  reclassificado.
- **A seção `## Declarado pelo dono` nunca é reescrita.** O perfil tem duas
  metades: o que se destila do código, que se regenera, e o que só uma pessoa
  sabe — política de branch, o que a sessão pode empurrar, quem aprova,
  particularidades de ambiente. Ao regenerar, **copie essa seção inteira,
  intacta**, para o perfil novo. Regeneração que apaga o declarado ensina o
  dono a não declarar nada.
- Sem âncora clara, o tipo é **indefinido**: uma linha no mapa e uma pergunta
  ao dono — a resposta vira declaração.
- Repositório de **infraestrutura nunca recebe varredura profunda de
  código**: o perfil é o contrato (entradas, saídas, onde se aplica).
- **A triagem é local; a atualização é um por vez.** Clone parado mente — o
  perfil sairia sem o trabalho dos outros. Antes de perfilar um repositório
  **do lote**, atualize a branch principal dele
  (`git -C <repo> pull --ff-only`), um de cada vez. Fora do lote, nada de
  fetch: rajada de rede na frota inteira é o que proxy bloqueia (403). Rede
  falhou? Perfile o clone como está e registre `"clone_atras": true` na
  entrada do índice.
- O sinal de mudança é **o SHA do git** — nunca data, mtime ou hash próprio.
- Estado se guarda no JSON; markdown nunca gera estado.
- Não re-perfile por mudança irrelevante (CHANGELOG, `.github/`).
- Conteúdo da wiki é privado do workspace. Nunca vai para repositório
  público, nem em exemplo.

## Ligar no AGENTS.md

Confira se o `AGENTS.md` da raiz aponta a wiki e o mapa. Sem o ponteiro, a
wiki existe e ninguém a lê.
