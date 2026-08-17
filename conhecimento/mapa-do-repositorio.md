# Mapa do repositório

O que existe depois de montar a camada, e o que entra em cada lugar.

## A árvore

```text
repositorio/
├── AGENTS.md                instruções neutras — quase todo agente lê
├── CLAUDE.md                adaptador do Claude Code: importa o AGENTS.md
├── configuracao-da-casa.md  onde as issues nascem — molde da camada, valor seu
├── ambiente.txt             o que a casa exige do ambiente — valor seu
├── montar.py                monta e atualiza a camada
├── .agents/
│   ├── skills/              fonte das skills: uma pasta por skill
│   ├── recibo/              contrato do recibo: schema + validador, --testar
│   └── conferir/            conferência declarado × executado, --testar
├── .claude/
│   ├── settings.json        permissões e ganchos do Claude Code
│   ├── hooks/               ganchos da camada
│   ├── commands/            qualquer .md aqui vira comando de barra
│   ├── skills/              cópia gerada — entra no git, não se edita aqui
│   └── agents/              subagentes: um arquivo por agente
├── .devin/
│   ├── config.json          desliga a leitura da .claude e guarda o deny próprio
│   └── skills/              skills que só o Devin enxerga
├── fluxos/                  processos passo a passo
├── conhecimento/            técnicas e ferramentas
├── site/                    o guia navegável — construção no README.md
├── tmp/                     rascunho e saída gerada — fora do git
├── projetos/                repositórios de código — fora do git da raiz
├── .credenciais/            senhas e chaves — fora de todo git
└── recursos/                material de terceiro — fora do git
```

As três últimas são o esqueleto do workspace: nascem só com
`python montar.py --esqueleto`, na raiz que abriga os repositórios. O
conteúdo fica fora do git; a pasta viaja pelo LEIAME liberado no ignore.

## O que a atualização sobrescreve — e o que é seu

| A camada sobrescreve (edite na origem)             | Seu — nunca reescrito                     |
| -------------------------------------------------- | ----------------------------------------- |
| páginas de `fluxos/` e `conhecimento/`             | `AGENTS.md` e `CLAUDE.md`                 |
| skills da camada em `.agents/skills/` e o espelho  | suas skills (pastas que a camada não tem) |
| ganchos em `.claude/hooks/`                        | suas páginas e arquivos com nome próprio  |
| arquivos do site (`site/…`)                        | `projetos/`, `.credenciais/`, `recursos/` |
| os ajustes garantidos na configuração              | o resto da configuração                   |

- Arquivo **seu** com o **mesmo caminho** de um da camada é tratado como da
  camada — dê nome próprio ao que é seu.
- Única exceção que acrescenta: se o seu `AGENTS.md` não citar
  `conhecimento/regras-da-camada.md`, a atualização acrescenta o endereço no
  fim — nunca as regras, nunca reescrevendo.

Os três canais de chegada de uma regra:

| Canal                       | Chega a quem já montou? | Lido em toda sessão?  |
| --------------------------- | ----------------------- | --------------------- |
| Página do guia              | sim                     | não — só se abrir     |
| `AGENTS.md`                 | não                     | sim                   |
| Gancho de início de sessão  | sim                     | sim, onde há gancho   |

Regra que manda consultar uma fonte entrega a fonte junto — nunca confie
que ela será buscada.

## A parte opcional

```bash
python montar.py --modulos          # o que existe, e o que já está aqui
python montar.py --modulo <nome>    # instala aquele
```

Sem pedir pelo nome, nenhum byte de módulo chega. `--atualizar` atualiza o
instalado e nunca instala o que falta. O motor de correntes (módulo
`encadeador`) está em [rodar uma corrente](../fluxos/rodar-uma-corrente.md).

## A ordem de atualizar

```bash
git status --short           # árvore suja? resolva antes
git pull --ff-only           # traga o que já subiu
python montar.py --atualizar
python montar.py --versao    # o número tem de bater com a origem
```

- Piso de migração: **0.88**. Casa mais velha roda a montagem de novo.
- Editou página da camada? A atualização sobrescreve — edite na origem.
- Apagou página da camada? O `--atualizar` a recria — tire na origem.

## A régua de markdown

O `.markdownlint.jsonc` da raiz cobra estrutura, não estética. Conserto:

```bash
npx --yes markdownlint-cli2 --fix "**/*.md" "#**/node_modules" "#projetos" "#recursos" "#.credenciais"
```

Régua de pasta (`.markdownlint.jsonc` dentro dela) vence a da raiz.

## Onde escrever cada coisa

| Você quer escrever                        | Vai em                                         |
| ----------------------------------------- | ---------------------------------------------- |
| Regra que vale para qualquer agente       | `AGENTS.md`                                    |
| Regra da lista numerada                   | `conhecimento/regras.json` — a página é gerada |
| Skill                                     | `.agents/skills/<nome>/SKILL.md`               |
| Processo passo a passo                    | `fluxos/`                                      |
| Técnica ou ferramenta genérica            | `conhecimento/`                                |
| **O que é seu**: nota, decisão, dia a dia | `conhecimento/<sua-subpasta>/`                 |
| Servidor MCP local                        | `.agents/mcp/<nome>/`                          |
| Só o Claude Code entende                  | `.claude/`                                     |
| Só o Devin entende                        | `.devin/`                                      |

Página nova entra com dois endereços de chegada: a linha no índice
(`site/sidebars.js`, escrito à mão, e o `LEIAME.md` da subpasta) **e** um
link vindo de página que já é lida. Na poda, a conta inverte: página sem
link de entrada é candidata a sair por definição. Regra geral carrega o
endereço das suas exceções.

Ao arrumar: todo achado cita a linha desta página ou do `AGENTS.md` que
decide; nada se apaga — o que está fora do lugar se **move** com `git mv`,
e destino ocupado vira pergunta. O pedido pronto:

```text
Proponha a arrumação das subpastas de conhecimento/ conforme as regras
desta página. Confira, citando em cada achado o endereço da regra:
um nível de subpasta; LEIAME.md de uma linha em cada; nome minúsculo sem
acento nem espaço; primeiro nível curto; pasta de um arquivo só; página
sem link de entrada; o que é da casa na camada, e o contrário.
PROPONHA: de → para → a regra que manda. Nada se apaga, e nada se move
sem meu OK.
```

## Pastas e site

- Pasta nova só quando: o material já cansa, nenhuma existente serve, e o
  primeiro nível continua curto (régua: só se paga tirando ~20 itens do
  nível de cima). Cada subpasta nasce com `LEIAME.md` de uma linha.
- Nome de pasta e arquivo: minúsculo, sem acento, sem espaço.
- Em `conhecimento/`: primeiro nível é da camada; subpasta é sua — a
  atualização nunca escreve nela.
- O site publica as páginas da camada e **um** nível de subpasta de
  `conhecimento/`; `.md` é markdown comum (não MDX) — `<coisa/assim>` não
  derruba a construção; componente pede `.mdx`.

## Onde abrir o agente

**Abra na raiz — a pasta que tem o `AGENTS.md`.**

| Você abre em | Regras   | Skills      |
| ------------ | -------- | ----------- |
| a raiz       | carregam | carregam    |
| uma subpasta | talvez   | **nenhuma** |

- Skill nunca sobe pasta; nada avisa.
- Numa subpasta, o `@AGENTS.md` do `CLAUDE.md` vira import externo e exige
  aprovação — sem ela, nem a regra chega.
- Para focar num lugar: `Trabalhe em <pasta>.` — em vez de abrir lá.

Diagnóstico do que carregou, em duas partes e nesta ordem:

```text
PARTE 1 — SEM ABRIR ARQUIVO NENHUM. Só do que já está carregado agora:
que instruções você recebeu (uma frase literal de cada arquivo de regra),
que skills, servidores MCP, ganchos e subagentes você enxerga. Não
consegue medir? Diga "não consigo medir" — não estime.

PARTE 2 — agora pode ler o disco. O que existe em .agents/skills/,
.claude/ e .devin/ que NÃO apareceu na Parte 1?
```

## Vários repositórios na mesma pasta

A camada na raiz; os repositórios numa pasta abaixo, cada um com seu git.
No `.gitignore` da raiz:

```text
/repositorios/*
!/repositorios/.gitkeep
```

- A barra inicial ancora na raiz; o asterisco ignora o conteúdo, não a
  pasta — com a exceção, a estrutura viaja no clone.
- `.gitignore` esconde do git e **da busca**, não da leitura — hábitos em
  [zero que mente](zero-que-mente.md).
- `CLAUDE.md` de repositório de baixo não entra na largada: só é lido ao
  abrir arquivo daquela pasta. Regra de primeiro segundo mora na raiz.
