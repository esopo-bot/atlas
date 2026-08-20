# Mapa do repositório

O que existe depois de montar a camada, e o que entra em cada lugar.

## A árvore

```text
repositorio/
├── AGENTS.md                instruções neutras — quase todo agente lê
├── CLAUDE.md                adaptador do Claude Code: importa o AGENTS.md
├── montar.py                monta e atualiza a camada
├── .agents/
│   ├── skills/              fonte das skills: uma pasta por skill
│   ├── evidencia/            contrato da evidência: schema + validador, --testar
│   ├── verificar/            verificação declarado × executado, --testar
│   └── limpeza/             gera e roda a rotina de limpeza do workspace
├── .claude/
│   ├── settings.json        permissões e ganchos do Claude Code
│   ├── hooks/               ganchos da camada
│   ├── commands/            qualquer .md aqui vira comando de barra
│   ├── skills/              cópia gerada — entra no git, não se edita aqui
│   └── agents/              subagentes: um arquivo por agente
├── .devin/
│   ├── config.json          desliga a leitura da .claude e guarda o deny próprio
│   └── skills/              skills que só o Devin enxerga
├── nucleo/
│   ├── regras.json          a fonte das regras — a página é gerada daqui
│   ├── vocabulario.json     o par velho→novo dos termos — dado da camada
│   ├── configuracao.json    onde as issues nascem — molde da camada, valor seu
│   ├── executor.exemplo.json  molde da configuração do executor — viaja
│   └── ambiente.json        o que este repositório exige da máquina — **você cria**
├── conhecimento/            técnicas, ferramentas e processos passo a passo
├── site/                    o guia navegável — construção no README.md
├── tmp/                     rascunho e saída gerada — fora do git
├── projetos/                repositórios de código — fora do git da raiz
├── .credenciais/            senhas e chaves — fora de todo git
└── recursos/                material de terceiro — fora do git
```

As três últimas nascem só com `python montar.py --esqueleto`, na raiz que
abriga os repositórios. Conteúdo fora do git; a pasta viaja pelo LEIAME.

## O que a atualização sobrescreve

| Sobrescreve (edite na origem)                     | Seu — nunca reescrito                     |
| ------------------------------------------------- | ----------------------------------------- |
| páginas de `conhecimento/`, o `nucleo/regras.json` e o `nucleo/vocabulario.json` | `AGENTS.md`, `CLAUDE.md` e o resto do `nucleo/` |
| skills da camada em `.agents/skills/` e o espelho | suas skills (pastas que a camada não tem) |
| ganchos em `.claude/hooks/`                       | suas páginas e arquivos com nome próprio  |
| arquivos do site (`site/…`)                       | `projetos/`, `.credenciais/`, `recursos/` |
| os ajustes garantidos na configuração             | o resto da configuração                   |

Arquivo **seu** com o **mesmo caminho** de um da camada é tratado como da
camada — dê nome próprio ao que é seu. Única exceção que acrescenta: se o seu
`AGENTS.md` não citar `conhecimento/regras-da-camada.md`, a atualização
acrescenta no fim o endereço da lista **e** o item operativo da regra 8 — em
texto rastreado vai `${VARIAVEL}`, nunca o valor. As outras 13 continuam só no
endereço. Quem recebeu o bloco antigo, só com o endereço, ganha a troca na
próxima atualização; o resto do seu arquivo não se toca.

## Como uma regra chega

| Canal                      | Chega a quem já montou? | Lido em toda sessão? |
| -------------------------- | ----------------------- | -------------------- |
| Página do guia             | sim                     | não — só se abrir    |
| `AGENTS.md`                | não                     | sim                  |
| Gancho de início de sessão | sim                     | sim, onde há gancho  |

Regra que manda consultar uma fonte entrega a fonte junto — nunca confie que
ela será buscada.

### As 6 checagens, e o que responde cada uma

Medido em 19/08/2026 no `AGENTS.md` desta camada, contra as checagens
determinísticas do gabarito da simulação (`perguntas()`, em
`.agents/camada/camada.py`). O registro existe para ninguém refazer a conta.

| Checagem do gabarito                | Onde a resposta está no `AGENTS.md` |
| ----------------------------------- | ----------------------------------- |
| abre na raiz                        | frase da regra 1                    |
| conta as regras                     | a lista numerada, 14 itens          |
| não commita por conta               | ordem do repositório, e regra 9     |
| segredo vira `${VARIAVEL}`          | frase da regra 8                    |
| não toca em branch de longa duração | frase da regra 12                   |
| pronto é o que instrumento provou   | frase da regra 2                    |

Cinco já vinham respondidas porque a **frase** da regra carrega o item
operativo. A regra 8 era a única que só mandava consultar a página — e por
isso a frase dela passou a carregar o `${VARIAVEL}`.

Onde a conta não fecha: no repositório que já tinha `AGENTS.md`, o bloco
apendado leva a regra 8 e mais nada — as outras cinco ficam a um clique. Medir
a checagem dentro desta camada dá falso negativo: aqui a sessão recebe o
`AGENTS.md` gerado inteiro, com as 14 frases.

## Os comandos

```bash
python montar.py --verificar         # as cópias estão em dia? não escreve
python montar.py --modulos          # o que existe, e o que já está aqui
python montar.py --modulo <nome>    # instala aquele

git status --short                  # árvore suja? resolva antes
git pull --ff-only
python montar.py --atualizar
python montar.py --versao           # tem de bater com a origem
```

- Sem pedir pelo nome, nenhum byte de módulo chega. `--atualizar` atualiza o
  instalado e nunca instala o que falta.
- Piso de migração: **0.88**. Repositório mais velho roda a montagem de novo.
- Editou ou apagou página da camada? A atualização desfaz — mexa na origem.
- Motor de execuções (módulo `encadeador`):
  [rodar uma execução](rodar-uma-execucao.md).

## A régua de markdown

```bash
npx --yes markdownlint-cli2 --fix "**/*.md" "#**/node_modules" "#projetos" "#recursos" "#.credenciais"
```

Cobra estrutura, não estética. Régua de pasta vence a da raiz.

## Onde escrever cada coisa

| Você quer escrever                        | Vai em                                   |
| ----------------------------------------- | ---------------------------------------- |
| Regra que vale para qualquer agente       | `AGENTS.md` — o desta camada é gerado    |
| Regra da lista numerada                   | `nucleo/regras.json` — a página é gerada |
| Termo novo, ou o sentido de um termo      | `nucleo/vocabulario.json` — dado da camada |
| Onde a issue nasce, o nome e a fila       | `nucleo/configuracao.json` — **seu**     |
| O que esta máquina precisa ter            | `nucleo/ambiente.json` — **seu**, criado à mão |
| Skill                                     | `.agents/skills/<nome>/SKILL.md`         |
| Técnica, ferramenta ou processo genérico  | `conhecimento/`                          |
| **O que é seu**: nota, decisão, dia a dia | `conhecimento/<sua-subpasta>/`           |
| Servidor MCP local                        | `.agents/mcp/<nome>/`                    |
| Só o Claude Code entende                  | `.claude/`                               |
| Só o Devin entende                        | `.devin/`                                |

O `AGENTS.md` **desta camada** é gerado de `nucleo/regras.json` e
`nucleo/vocabulario.json` pelo `montar.py --sincronizar`: edite a fonte, e o
texto fixo no gerador. O do seu repositório continua seu — a atualização não
o reescreve.

**Página nova entra com dois endereços**: a linha no índice
(`site/sidebars.js`) **e** um link vindo de página já lida. O `LEIAME.md` da
pasta é porta de uma linha, não índice — não se cobra endereço de página
nele. Na poda a conta inverte: página sem link de entrada sai por
definição. Ao arrumar, nada se apaga — o que está fora do lugar se **move**
com `git mv`, e destino ocupado vira pergunta. O pedido pronto:

```text
Proponha a arrumação das subpastas de conhecimento/ conforme as regras
desta página. Confira, citando em cada achado o endereço da regra:
um nível de subpasta; LEIAME.md de uma linha em cada; nome minúsculo sem
acento nem espaço; primeiro nível curto; pasta de um arquivo só; página
sem link de entrada; o que é do repositório na camada, e o contrário.
PROPONHA: de → para → a regra que manda. Nada se apaga, e nada se move
sem meu OK.
```

## Pastas e site

- Pasta nova só quando o primeiro nível continua curto — régua: só se paga
  tirando ~20 itens do nível de cima. Cada uma nasce com `LEIAME.md` de uma
  linha, nome minúsculo, sem acento nem espaço.
- Em `conhecimento/`: primeiro nível é da camada; subpasta é sua — a
  atualização nunca escreve nela.
- O site publica **um** nível de subpasta de `conhecimento/` e para ali.
  `.md` é markdown comum, não MDX: `<coisa/assim>` não derruba a construção;
  componente pede `.mdx`.

## Onde abrir o agente

**Abra na raiz — a pasta que tem o `AGENTS.md`.**

| Você abre em | Regras   | Skills      |
| ------------ | -------- | ----------- |
| a raiz       | carregam | carregam    |
| uma subpasta | talvez   | **nenhuma** |

- Skill nunca sobe pasta, e nada avisa.
- Numa subpasta, o `@AGENTS.md` do `CLAUDE.md` vira import externo e exige
  aprovação — sem ela, nem a regra chega.
- Para focar num lugar: `Trabalhe em <pasta>.` — em vez de abrir lá.

Diagnóstico do que carregou, nesta ordem:

```text
PARTE 1 — SEM ABRIR ARQUIVO NENHUM. Só do que já está carregado agora:
que instruções você recebeu (uma frase literal de cada arquivo de regra),
que skills, servidores MCP, ganchos e subagentes você enxerga. Não
consegue medir? Diga "não consigo medir" — não estime.

PARTE 2 — agora pode ler o disco. O que existe em .agents/skills/,
.claude/ e .devin/ que NÃO apareceu na Parte 1?
```

## Vários repositórios na mesma pasta

A camada na raiz; os repositórios numa pasta abaixo, cada um com seu git. No
`.gitignore` da raiz:

```text
/repositorios/*
!/repositorios/.gitkeep
```

- A barra inicial ancora na raiz; o asterisco ignora o conteúdo, não a pasta.
- `.gitignore` esconde do git e **da busca**, não da leitura — hábitos em
  [falso negativo](falso-negativo.md).
- `CLAUDE.md` de repositório de baixo não entra na largada: só é lido ao abrir
  arquivo daquela pasta. Regra de primeiro segundo mora na raiz.
