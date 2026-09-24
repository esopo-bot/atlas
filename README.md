# atlas

Camada compartilhável de skills e conhecimento para agentes de IA.

Em linguagem comum: isto instala, em qualquer repositório seu, um conjunto de
instruções, skills e conhecimento que Claude Code, Codex, Devin ou outro agente
passam a seguir — o mesmo jeito de trabalhar, em toda máquina. Todo o conteúdo
é genérico: serve a qualquer pessoa.

## O que vem dentro

- **As regras**, numeradas e citadas por número:
  [regras da camada](conhecimento/regras-da-camada.md). Elas nascem de um
  arquivo de dados, não de prosa — a página é gerada.
- **Páginas de saber** ([conhecimento](conhecimento/)): o que segura cada
  regra na prática, investigação de incidente, o estado que não viaja da sua
  máquina. O índice da pasta lista o que existe hoje.
- **Skills prontas** ([.agents/skills](.agents/skills/)): a lista viva é a
  descrição de cada `SKILL.md` — veja com `ls .agents/skills/`.
- **Cercas que recusam na hora** ([.claude/hooks](.claude/hooks/)): escrita em
  cópia gerada, comentário explicativo, branch protegida, credencial,
  território de outro repositório. Elas não avisam: elas negam, e a recusa diz
  a regra, o endereço do valor certo e o que fazer. Elas valem no Claude Code
  e, com `--devin`, também na outra ferramenta — a mesma lista de cercas,
  sem um segundo lugar para manter.
- **Um ritual de verificação**: uma porta única que roda as rotinas
  permanentes e falha se alguma cair. Veja o catálogo com
  `python verificacoes.py --listar`.
- **Um script**: [montar.py](montar.py) instala tudo isso, em qualquer
  repositório, e atualiza sem apagar o que é seu.

## O que ela cobra

Toda sessão paga a camada antes de fazer qualquer coisa: as instruções, o
catálogo das skills e o que os ganchos de abertura injetam. O corpo de cada
skill **não** entra nessa conta — ele só é lido quando a skill dispara.

```bash
python .agents/camada/camada.py --largada
```

O teto mora em `nucleo/configuracao.json`, campo `teto_da_largada_em_bytes`,
e é seu: baixe-o e a rotina passa a cobrar. Número escrito envelhece — o
comando acima é a fonte, do gasto e do teto.

A mesma rotina avisa quando a listagem de skills que a **sua ferramenta** monta
passa do orçamento dela: acima disso a ferramenta corta descrições, e skill sem
descrição deixa de ser encontrada. Isso não é do repositório, e por isso ela
avisa em vez de reprovar.

## O que a diferencia

**Prova que se re-executa.** Cada etapa de um trabalho grava a afirmação, o
comando e a saída — e um auditor separado **re-roda** os comandos depois e
acusa o que não reproduz mais. Prova que envelheceu é achado, não silêncio.

**Toda cerca viaja.** Uma rotina cobra o saldo entre o que este repositório
tem e o que o instalador carrega: gancho ligado aqui e ausente do pacote é
acusado pelo nome. Bloqueio que não chega a quem instala não é bloqueio.

## Começar em dois passos

Clone este repositório numa pasta ao lado e, de dentro do seu repositório,
rode o instalador que mora no clone:

```bash
python <pasta do clone do atlas>/montar.py
```

Deu certo quando terminar com `Pronto.` e a lista do que foi criado. O
instalador lê a camada da pasta em que mora, e só o que o git rastreia ali:
arquivo solto no clone não viaja. Pasta que não é repositório git é recusada,
com o recado de clonar.

Se a pasta for a raiz de um workspace — a que abriga os repositórios —, use
`python <pasta do clone do atlas>/montar.py --esqueleto` no primeiro passo:
cria também `projetos/`, `.credenciais/` e `recursos/`.

Se você trabalha noutra ferramenta de agente além do Claude Code, use
`python <pasta do clone do atlas>/montar.py --devin --escrever` para o Devin, ou `python <pasta do clone do atlas>/montar.py --codex --escrever` para o Codex; sem `--escrever`, as duas bandeiras só mostram o que gravariam: as cercas passam a valer lá também, pela ponte, no dialeto de cada agente. O Copilot não precisa de bandeira: com a pasta confiada, ele roda direto as cercas do `.claude/settings.json`.
Sem a bandeira nada é escrito para ela — quem não usa não ganha pasta que não
pediu. Para verificar que atravessaram, sem abrir sessão nenhuma:

```bash
python .agents/travessia/travessia.py
```

## Atualizar uma máquina que já tem a camada

Traga o clone em dia com `git pull` e, de dentro do seu repositório, rode:

```bash
python <pasta do clone do atlas>/montar.py --atualizar
```

A atualização **só toca o que veio da camada**. `AGENTS.md`, `CLAUDE.md`,
suas skills e seus arquivos ficam intactos — a fronteira completa é o que o
git rastreia na pasta da camada: o que não está lá, ele não toca. O que a
camada instalou fica listado em `.agents/camada/registro-da-instalacao.json`,
com o commit do clone de onde veio. Instalou pela receita antiga, com o
`montar.py` copiado para a raiz? A atualização pelo clone funciona por cima
dela, e o `montar.py` antigo fica onde está: apagar é decisão sua. A exceção
declarada é o `.mcp.json` que você mesmo escreveu: cada servidor dele entra
em `allowedMcpServers` do seu `.claude/settings.local.json` e no
`.devin/mcp_config.local.json`, os dois pessoais e fora do git. É o que
devolve o servidor à sessão onde a organização aplica uma lista branda de
MCP, e o que faz o Devin enxergar os mesmos servidores.
Para saber se a instalação está atrás do clone, rode, de dentro do seu
repositório, `python <pasta do clone do atlas>/montar.py --verificar`: ele
nomeia cada arquivo atrás.

## Regras do repositório

Só é pronto o que um instrumento provou — build, teste, listagem; nunca "o
modelo disse". E nada pessoal entra aqui: este repositório é público desde o
primeiro commit.

## Licença

[MIT](LICENSE).
