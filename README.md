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
  `python verificacoes.py --lista`.
- **Um script**: [montar.py](montar.py) instala tudo isso, em qualquer
  repositório, e atualiza sem apagar o que é seu.

## O que ela cobra

Toda sessão paga a camada antes de fazer qualquer coisa: as instruções, o
catálogo das skills e o que os ganchos de abertura injetam. O corpo de cada
skill **não** entra nessa conta — ele só é lido quando a skill dispara.

```bash
python .agents/camada/camada.py --largada
```

Hoje, neste repositório, são pouco mais de oito mil bytes contra um teto de
dez mil declarado em `nucleo/configuracao.json`. O teto é seu: baixe-o e a
rotina passa a cobrar. Número escrito envelhece — o comando acima é a fonte.

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

Copie `montar.py` para a raiz do seu repositório e:

```bash
python montar.py
```

Deu certo quando terminar com `Pronto.` e a lista do que foi criado.

Se a pasta for a raiz de um workspace — a que abriga os repositórios —, use
`python montar.py --esqueleto` no primeiro passo: cria também `projetos/`,
`.credenciais/` e `recursos/`.

Se você trabalha noutra ferramenta de agente além do Claude Code, use
`python montar.py --devin`: as cercas passam a valer lá também, pela ponte.
Sem a bandeira nada é escrito para ela — quem não usa não ganha pasta que não
pediu. Para verificar que atravessaram, sem abrir sessão nenhuma:

```bash
python3 .agents/travessia/travessia.py
```

## Atualizar uma máquina que já tem a camada

Substitua o `montar.py` pelo novo e rode:

```bash
python montar.py --atualizar
```

A atualização **só toca o que veio da camada**. `AGENTS.md`, `CLAUDE.md`, o
`settings.local.json`, suas skills e seus arquivos ficam intactos — a
fronteira completa é o que `montar.py` carrega embutido: o que não está
lá, ele não toca.
Todo comando imprime `camada 0.N`: número menor que o da origem significa
atualização pendente.

## Regras do repositório

Só é pronto o que um instrumento provou — build, teste, listagem; nunca "o
modelo disse". E nada pessoal entra aqui: este repositório é público desde o
primeiro commit.

## Licença

[MIT](LICENSE).
