# atlas

Camada compartilhável de skills, fluxos e conhecimento para agentes de IA.

Em linguagem comum: isto instala, em qualquer repositório seu, um conjunto de
instruções, fluxos e skills que Claude Code, Codex, Devin ou outro agente
passam a seguir — o mesmo jeito de trabalhar, em toda máquina. Todo o conteúdo
é genérico: serve a qualquer pessoa.

## O que vem dentro

- **Um guia curto** ([fluxos](fluxos/) e [conhecimento](conhecimento/)):
  comece por [Comece aqui](conhecimento/comece-aqui.md).
- **Skills prontas** ([.agents/skills](.agents/skills/)): padrão de qualidade
  de código (injetado por gancho), wiki local de projetos, procurar antes de
  criar, e mais — a lista viva está em
  [as skills da camada](conhecimento/skills-da-camada.md).
- **Um script**: [montar.py](montar.py) instala tudo isso, em qualquer
  repositório, e atualiza sem apagar o que é seu.

## Começar em dois passos

Copie `montar.py` para a raiz do seu repositório e:

```bash
python montar.py
```

Deu certo quando terminar com `Pronto.` e a lista do que foi criado.

Se a pasta for a raiz de um workspace — a que abriga os repositórios —, use
`python montar.py --esqueleto` no primeiro passo: cria também `projetos/`,
`.credenciais/` e `recursos/`. Para ver o guia como site, um comando por
linha — `&&` não existe no Windows PowerShell:

```bash
cd site
npm install
npm run build
```

## Atualizar uma máquina que já tem a camada

Substitua os dois scripts pelos novos e rode:

```bash
python montar.py --atualizar
```

A atualização **só toca o que veio da camada**. `AGENTS.md`, `CLAUDE.md`, o
`settings.local.json`, suas skills e seus arquivos ficam intactos — a
fronteira completa está no
[mapa do repositório](conhecimento/mapa-do-repositorio.md).
Todo comando imprime `camada 0.N`: número menor que o da origem significa
atualização pendente. As mudanças de cada versão estão no
[CHANGELOG](CHANGELOG.md).

## Regras da casa

Só é pronto o que um instrumento provou — build, teste, listagem; nunca "o
modelo disse". E nada pessoal entra aqui: este repositório é público desde o
primeiro commit.

## Licença

[MIT](LICENSE).
