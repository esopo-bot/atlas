# Mapa do repositório

O que existe depois de montar a camada, e o que entra em cada lugar.

## A árvore

```
repositorio/
├── AGENTS.md              instruções neutras — o centro que quase todo agente lê
├── CLAUDE.md              adaptador do Claude Code: importa o AGENTS.md
├── configuracao-da-casa.md  onde as issues desta casa nascem — molde da camada, valor seu
├── montar.py              monta e atualiza a camada — você copia para cá
│
├── .agents/skills/        fonte das skills: uma pasta por skill
│
├── .claude/
│   ├── settings.json      permissões do Claude Code e o gancho da qualidade
│   ├── .gitignore         tira do git o que é gerado e o que é pessoal
│   ├── hooks/             ganchos da camada: a qualidade entra por aqui
│   ├── commands/          forma antiga de escrever skill
│   ├── skills/            cópia gerada — entra no git, mas não se edita aqui
│   └── agents/            subagentes: um arquivo por agente
│
├── .devin/
│   ├── config.json        permissões e a ponte que manda ler a .claude
│   └── skills/            skills que só o Devin enxerga
│
├── fluxos/                processos passo a passo
├── conhecimento/          técnicas e ferramentas
├── .markdownlint.jsonc    a régua de markdown — o editor lê daqui
│
├── tmp/                   rascunho e saída gerada — descartável, fora do git
├── projetos/              os repositórios de código — fora do git da raiz
├── .credenciais/          senhas e chaves — fora de todo git
├── recursos/              material de terceiro — fora do git
└── .gitignore             com as linhas que mantêm isso assim
```

As três pastas do fim são o esqueleto do workspace e **só nascem com
`python montar.py --esqueleto`** — a opção é para a raiz que abriga os
repositórios. Rodado sem ela, num repositório de projeto, o script traz só a
camada: uma pasta `projetos/` dentro de um projeto não faz sentido.

O **conteúdo** das três fica fora do git — cada projeto já tem o seu, e
segredo não entra em git nenhum, nem em repositório privado. Mas a **pasta em
si viaja**: o `.gitignore` que o `montar.py` escreve ignora o conteúdo
(`/projetos/*`) e libera o LEIAME de cada uma, que segura a estrutura no git.
Clonou o workspace noutra máquina: as pastas chegam vazias, com a explicação
dentro — e os segredos ficam onde estavam.

## O que a atualização sobrescreve — e o que é seu

O `montar.py --atualizar` traz a versão nova da camada para um repositório que
já a tem. A fronteira é fixa:

| A camada sobrescreve (edite na origem, não aqui)     | Seu — nunca reescrito                     |
| ---------------------------------------------------- | ----------------------------------------- |
| as páginas do guia em `fluxos/` e `conhecimento/`    | `AGENTS.md` e `CLAUDE.md`                 |
| as skills da camada em `.agents/skills/` e o espelho | suas skills (pastas que a camada não tem) |
| os ganchos em `.claude/hooks/`                       | suas páginas e arquivos com nome próprio  |
| os arquivos do site (`site/…`)                       | `projetos/`, `.credenciais/`, `recursos/` |
| os ajustes garantidos na configuração                | o resto da configuração                   |

Uma armadilha com nome: arquivo **seu** com o **mesmo caminho** de um da
camada é tratado como da camada — a atualização o sobrescreve. Dê nome próprio
ao que é seu.

**A única exceção, e ela acrescenta:** se o seu `AGENTS.md` não citar
`conhecimento/regras-da-camada.md`, a atualização acrescenta três linhas no
fim dele com esse endereço. Não reescreve nada, não reordena, e não repete as
regras — só o endereço. O porquê está logo abaixo.

### Os três canais, e nenhum tem as duas propriedades

Toda regra da camada chega por um destes caminhos, e a escolha decide se
alguém vai lê-la:

| Canal | Chega a quem já montou? | Lido em toda sessão? |
| --- | --- | --- |
| Página do guia (`fluxos/`, `conhecimento/`) | **sim** — a atualização reescreve | **não** — só se você abrir |
| `AGENTS.md` | **não** — a atualização nunca o reescreve | **sim** |
| Gancho de início de sessão | **sim** | **sim**, onde a ferramenta tiver gancho |

É por isso que o ponteiro acima existe: **quando uma regra manda consultar uma
fonte, a camada entrega a fonte — não confia que ela será buscada.**

### A parte opcional

Nem tudo da camada serve a todo repositório. O que só vale para quem usa uma
ferramenta específica vive em **módulo**, e módulo não chega sozinho:

```bash
python montar.py --modulos          # o que existe, e o que já está aqui
python montar.py --modulo <nome>    # instala aquele
```

Sem pedir pelo nome, **nenhum byte** de módulo nenhum chega ao seu
repositório. E `--atualizar` atualiza o que você já instalou, mas nunca
instala o que falta — o que você não pediu, você continua sem.

Um módulo pode trazer página no primeiro nível de `conhecimento/` e molde
**dentro de uma subpasta** — escrito uma vez e nunca mais; o que nascer ali é
seu. A fronteira do nível é a de sempre, em "Quando criar mais uma pasta".

A versão diz se vale atualizar: todo comando imprime `camada 0.N` (ou pergunte
com `python montar.py --versao`). Máquina com número menor está atrasada —
substitua o `montar.py` pelo novo e rode `python montar.py --atualizar`.

### A ordem de atualizar

Se o repositório tem remoto, a atualização **começa antes do script**: traga
o que já foi empurrado, senão você empilha a camada nova sobre uma árvore
velha — e o conflito aparece no pior momento, com a camada no meio.

```bash
git status --short           # árvore suja? commite ou guarde antes de trazer
git pull --ff-only           # o que outra sessão ou outra máquina já subiu
python montar.py --atualizar # agora sim, a camada
python montar.py --versao    # confere que o número bateu com a origem
```

Repositório sem remoto pula o meio — não há o que trazer.

Dois casos de borda, com resposta:

- **Editei uma página que é da camada.** A próxima atualização sobrescreve a
  sua edição. Edite na origem — o repositório da camada — ou copie o texto
  para um arquivo com nome seu.
- **Apaguei uma página da camada.** O `--atualizar` a recria. O que você não
  quer no destino, tira-se na origem.

## A régua de markdown

A camada traz um `.markdownlint.jsonc` na raiz, e ele cobra pouco de
propósito: estrutura do texto, sim; tamanho de linha e alinhamento de tabela,
não — **aviso que ninguém atende ensina a ignorar aviso.**

O editor lê essa régua sozinho. Quer mais disciplina numa pasta sua? Ponha um
`.markdownlint.jsonc` dentro dela: configuração de pasta vence a da raiz, e a
sua escolha não volta atrás na próxima atualização.

O conserto não roda sozinho. Um comando varre todos os `.md` do repositório e
resolve o grosso (precisa de Node). As linhas com `#` param nas fronteiras:
dependências, os repositórios dentro de `projetos/` e o material de terceiro
têm régua própria, e na gaveta de credenciais ferramenta nenhuma mexe:

```bash
npx --yes markdownlint-cli2 --fix "**/*.md" "#**/node_modules" "#projetos" "#recursos" "#.credenciais"
```

O que sobrar é linha comprida de texto corrido — requebre em 80 colunas, ou
peça isso ao agente. A skill `wiki-de-projetos` já roda o conserto sozinha ao
gerar perfis.

## Onde escrever cada coisa

| Você quer escrever                        | Vai em                           |
| ----------------------------------------- | -------------------------------- |
| Uma regra que vale para qualquer agente   | `AGENTS.md`                      |
| Uma skill                                 | `.agents/skills/<nome>/SKILL.md` |
| Um processo passo a passo                 | `fluxos/`                        |
| Uma técnica ou ferramenta genérica        | `conhecimento/`                  |
| **O que é seu**: nota, decisão, dia a dia | `conhecimento/<sua-subpasta>/`   |
| Um servidor MCP local                     | `.agents/mcp/<nome>/`            |
| Algo que só o Claude Code entende         | `.claude/`                       |
| Algo que só o Devin entende               | `.devin/`                        |

### Quando o agente for arrumar

Duas travas, e as duas nasceram de estrago:

- **Sem a citação da regra, não é achado.** Todo "isto está no lugar errado"
  vem com a linha desta página ou do `AGENTS.md` que decide. Sem isso o agente
  arruma por gosto — e arrumação por gosto é a que você desfaz na semana
  seguinte.
- **Nada se apaga**, nem duplicata, nem arquivo que parece morto. O que está
  fora do lugar se **move** com `git mv`, que preserva a história; se já
  existe arquivo no destino, os dois são relatados e a pergunta volta para
  você. Sessão que "limpa" duplicata escolhe sozinha qual das duas versões era
  a verdadeira — e escolhe errado na hora que importa.

O pedido pronto, para quando quiser essa arrumação:

```
Proponha a arrumação das subpastas de conhecimento/ conforme as regras
desta página. Confira, citando em cada achado o endereço da regra:

- um nível de subpasta, nunca dois — o site para no segundo;
- LEIAME.md de uma linha em cada subpasta;
- nome minúsculo, sem acento e sem espaço;
- o primeiro nível de conhecimento/ continua curto;
- pasta de um arquivo só — cobra pedágio e não paga;
- página sem link de entrada;
- o que é da casa e deveria estar na camada, e o contrário.

PROPONHA: de → para → a regra que manda. Nada se apaga, e nada se move
sem meu OK. Sem a citação da regra, não é achado.
```

### Quando criar mais uma pasta

Três condições, juntas: o material **já** cansa a leitura (pasta por
antecipação, com um arquivo só, cobra pedágio e não paga nada); nenhuma pasta
existente serviria; e o primeiro nível continua curto. A régua que usamos:
**uma pasta só se paga quando tira mais de umas vinte coisas do nível de
cima**. Largo e raso acha mais rápido que fundo e estreito.

E o que faz achar depois não é a arrumação: é o **índice**. Cada subpasta
nasce com um `LEIAME.md` de uma linha dizendo o que mora ali — sem isso, em
seis meses ninguém lembra, nem você nem o agente.

Nome de pasta e de arquivo em minúsculo, sem acento e sem espaço. Não é
preciosismo: acento é gravado diferente em cada sistema, e em Windows o git
funde `Docs/` com `docs/` sem avisar.

Em `conhecimento/`, a fronteira é o nível: **o primeiro nível é da camada;
subpasta é sua** — a atualização nunca escreve nela. A wiki dos projetos
(`conhecimento/projetos/`) já segue essa regra; crie as suas ao lado dela —
`notas/` para o dia a dia, `decisoes/` para decisão com motivo, os nomes são
seus. Quando uma nota amadurecer em lição genérica, ela muda de endereço:
vira página da camada, no repositório da camada.

### O que o site publica

As páginas da camada e **um nível de subpasta** de `conhecimento/` — o que
você escreve na sua subpasta aparece no site, sem configurar nada. O menu se
divide igual: as páginas da camada em ordem escrita à mão, e depois uma
categoria por subpasta sua, descoberta na construção (nome livre; o título do
`LEIAME.md` da subpasta vira o rótulo).

Um nível só, de propósito: o site enxerga a raiz do repositório, e um alcance
maior arrastaria os repositórios de código e o material de terceiro para
dentro da documentação.

E os arquivos `.md` são lidos como markdown comum, não como MDX. É o que
permite conteúdo gerado e nota pessoal escreverem `<coisa/assim>` no meio do
texto sem derrubar a construção. Quem precisar de componente escreve `.mdx`.

## Onde abrir o agente

**Abra na raiz — a pasta que tem o `AGENTS.md`.** Onde você abre decide o que
carrega, e a diferença é grande:

| Você abre em | Regras   | Skills      |
| ------------ | -------- | ----------- |
| a raiz       | carregam | carregam    |
| uma subpasta | talvez   | **nenhuma** |

**Skill nunca sobe pasta.** Aberto numa subpasta, o `.claude/skills/` da raiz
simplesmente não existe para o agente. Nada quebra e nada avisa: a sessão roda
sem nenhuma das suas skills, ganchos e subagentes.

**Regra sobe, mas tem uma armadilha.** O `CLAUDE.md` da raiz costuma ser só a
linha `@AGENTS.md`. Aberto numa subpasta, esse import aponta para fora do
diretório de trabalho — e import de fora exige uma aprovação sua. Sem ninguém
para aprovar, ele fica desligado em silêncio, e nem a regra chega.

Para trabalhar num lugar específico, **diga qual em vez de abrir lá**:

```
Trabalhe em <pasta do projeto>.
<o resto do seu pedido>
```

Assim você tem as duas coisas: tudo carregado e o foco no lugar certo.

### Como saber o que o agente de fato carregou

A falha acima é silenciosa, então a pergunta "chegou?" precisa de resposta
medida. Peça o diagnóstico em **duas partes, nesta ordem** — a ordem é o que
faz a medição valer:

```
PARTE 1 — SEM ABRIR ARQUIVO NENHUM. Só do que já está carregado agora:
que instruções você recebeu (cite uma frase literal de cada arquivo de
regra), que skills você enxerga, que servidores MCP estão ligados, que
ganchos e subagentes existem para você. Não consegue medir algo? Diga
"não consigo medir" — não estime.

PARTE 2 — agora pode ler o disco. O que existe em .agents/skills/,
.claude/ e .devin/ que NÃO apareceu na Parte 1? Cada item é uma peça que
o repositório tem e você não recebeu.
```

**`SEM ABRIR ARQUIVO NENHUM` é a linha que segura.** Com leitura liberada o
agente abre o disco e responde certo sobre o que nunca carregou — o falso
positivo que faz a camada parecer instalada quando não está. A Parte 2 existe
só para medir a distância entre as duas respostas.

## Vários repositórios na mesma pasta

A camada fica na raiz; os repositórios ficam numa pasta abaixo, cada um com o
seu git:

```
raiz/                    <- abra aqui
├── AGENTS.md
├── CLAUDE.md
├── .claude/
├── .gitignore           <- precisa ignorar a pasta de baixo
└── repositorios/
    ├── um/              git próprio
    └── outro/           git próprio
```

Três coisas medidas sobre este arranjo:

**Repositório dentro de repositório não atrapalha o agente.** Abrindo na raiz,
as skills carregam normalmente mesmo com repositórios próprios logo abaixo.

**Mas atrapalha o git.** Sem ignorar, a pasta aparece como não rastreada e um
`git add -A` a arrasta para dentro. Duas linhas resolvem:

```
/repositorios/*
!/repositorios/.gitkeep
```

A barra na frente ancora na raiz — sem ela, o git esconderia qualquer pasta
com esse nome, em qualquer profundidade. O asterisco ignora o conteúdo, não a
pasta: com um `.gitkeep` (ou LEIAME) liberado na exceção, a estrutura viaja no
clone; pasta ignorada inteira não chega em máquina nenhuma.

**`.gitignore` esconde do git, não da leitura.** A pasta ignorada continua
legível e editável normalmente — é exatamente o que se quer aqui. Mas ela
**some da busca**: ferramenta de busca respeita o ignore e devolve zero em
silêncio para termo que existe. Medido, e com os hábitos que resolvem, em
[zero que mente](zero-que-mente.md).

E o `CLAUDE.md` de um repositório de baixo **não entra na largada**: ele só é
lido quando o agente abre um arquivo daquela pasta. Regra que precisa valer
desde o primeiro segundo mora na raiz, nunca lá embaixo.
