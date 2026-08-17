# Ganchos: a regra que roda sozinha

Gancho é um programa que o agente executa em pontos fixos da sessão. Ele não
pede licença e não depende de o modelo lembrar da regra.

## Regra de texto ou gancho?

| Você quer                                       | Use                      |
| ----------------------------------------------- | ------------------------ |
| Negar um comando que um padrão descreve inteiro | regra em `settings.json` |
| Decidir olhando o comando de verdade            | gancho                   |
| Injetar informação no começo da sessão          | gancho                   |
| Conferir alguma coisa depois de cada edição     | gancho                   |

O caso que decide: `git push origin +feature/x` é push forçado e
`git push origin feature/x` não é. Nenhum padrão de texto separa os dois sem
errar de um lado. Um gancho lê o comando e separa.

E dá para saber qual das duas te barrou pelo texto da recusa: o `deny` do
`settings.json` nega curto e sem lição — não há programa do outro lado para
explicar; o gancho nega ou orienta **com a lição junto**, porque quem escreve
o motivo é ele (o contrato, abaixo).

## Onde se liga

No `settings.json`, por evento e por alvo:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "command": "python ${CLAUDE_PROJECT_DIR}/.claude/hooks/veto.py" }
        ]
      }
    ]
  }
}
```

O `matcher` aceita nomes de ferramenta separados por `|`, o `*` para todas, e
também o nome de uma ferramenta de MCP. O `${CLAUDE_PROJECT_DIR}` faz o caminho
valer em qualquer máquina.

## Os eventos que resolvem o dia a dia

| Evento                           | Dispara                     | Serve para                           |
| -------------------------------- | --------------------------- | ------------------------------------ |
| `PreToolUse`                     | antes de a ferramenta rodar | negar o que não pode acontecer       |
| `PostToolUse`                    | depois que ela rodou        | conferir o que acabou de mudar       |
| `SessionStart`                   | ao abrir a sessão           | injetar o que o agente precisa saber |
| `Stop`                           | ao terminar o turno         | fechar pendência, limpar estado      |
| `SubagentStart` / `SubagentStop` | em volta do subagente       | exigir registro do que ele fez       |

## O contrato

O gancho recebe um JSON no stdin e responde pelo que imprime.

**Deixar passar** é sair `0` calado, sem imprimir nada:

```python
sys.exit(0)
```

**Negar**, num `PreToolUse`:

```python
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "explique aqui o porquê, e qual é o caminho certo",
}}))
sys.exit(0)
```

**Injetar contexto**, num `SessionStart`:

```python
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "o que o agente precisa saber agora",
}}))
sys.exit(0)
```

O texto da recusa é lido pelo agente. Escreva o motivo e a saída, não só o
"não" — senão ele tenta a mesma coisa por outro caminho.

## Quatro armadilhas medidas

**Gancho de caminho relativo prende o shell.** O comando do gancho roda a
partir do cwd do shell da sessão — e o cwd anda com cada `cd`. Registrado
como `python .claude/hooks/x.py`, o gancho deixa de ser encontrado quando o
shell entra numa subpasta; num `PreToolUse` de shell, o erro passa a vetar
**todo comando — inclusive o `cd` de volta**. É um impasse fechado: o único
comando que sairia da subpasta é justamente o que o gancho recusa. O
conserto é o `${CLAUDE_PROJECT_DIR}` do exemplo acima, e a camada já
registra assim. A saída de emergência, se acontecer: as ferramentas de
arquivo não passam por esse gancho — corrija o `settings.json` por elas.

**Passagem é silêncio.** Emitir `permissionDecision: "defer"` no caminho de
passagem mata a chamada de ferramenta dentro de um subagente. Para deixar
passar, saia `0` sem imprimir.

**O nome do programa é o basename.** Comparar o primeiro token com `git` deixa
passar `git.exe`, `/usr/bin/git` e o caminho absoluto com espaço no meio. Use o
nome do arquivo, em minúsculas:

```python
if Path(token.replace("\\", "/")).name.lower() not in {"git", "git.exe"}:
    return False
```

E o verbo nem sempre é o segundo token: `git -C caminho push` e
`git -c chave=valor push` põem bandeiras antes dele, e algumas comem o token
seguinte.

**Gancho falha aberto, de propósito.** Entrada quebrada não pode prender a
sessão, então o caminho de erro é `sys.exit(0)`. A consequência: se o gancho não
subir, não existe proteção nenhuma. Por isso a regra de texto continua no
`settings.json` como rede de baixo. É sobreposição declarada, não descuido.

## Os ganchos que a camada traz

| Gancho                       | Evento         | O que faz                                              |
| ---------------------------- | -------------- | ------------------------------------------------------ |
| `injetar-qualidade.py`       | `SessionStart` | entrega o padrão de código, que skill nenhuma dispara   |
| `conferir-mcp.py`            | `SessionStart` | acusa declaração de MCP apontando para arquivo que não existe |
| `conferir-ambiente.py`       | `SessionStart` | acusa o que a máquina não tem e a casa declara precisar |
| `vetar-branch-protegida.py`  | `PreToolUse`   | recusa apagar, renomear e forçar branch de longa duração |
| `orientar-credencial.py`     | `PreToolUse`   | ensina ao ler credencial (shell e leitura direta); veta só o que não se desfaz |

O porquê do `conferir-mcp.py` está na [página de MCP](mcp.md). Ele carrega o
próprio teste: `python .claude/hooks/conferir-mcp.py --testar`.

O `conferir-ambiente.py` é o irmão dele para o resto da máquina: as
variáveis `${VAR}` do `.mcp.json` e o que o `ambiente.txt` da raiz declarar
— comando, pasta, arquivo, variável. Nomes e existência, nunca valores. O
`ambiente.txt` **é seu**, como a lista de branches: a atualização conserta o
código do gancho e nunca reescreve a sua declaração. O porquê está em
[o estado que não viaja](estado-que-nao-viaja.md). Ele carrega o próprio
teste: `python .claude/hooks/conferir-ambiente.py --testar`.

O veto de branch é a regra 12 virando trava. Os nomes protegidos vêm de
`.claude/branches-protegidas.txt` — um por linha, **e esse arquivo é seu**: a
atualização traz o conserto do código e nunca reescreve a sua lista. Ele
carrega o próprio teste:
`python .claude/hooks/vetar-branch-protegida.py --testar`.

E tem um limite declarado: **push normal para branch protegida passa.** Quem
decide isso é a regra 9 e o perfil do repositório. O gancho cuida do
destrutivo — apagar, renomear, reescrever.

O professor de credencial é o princípio *trava no que não se desfaz;
instrumento educativo em todo o resto* virando código. Ele olha o **alvo**
do comando, nunca o verbo — `cat`, `less`, `grep`, `Get-Content` e
`python -c open(...)` abrem arquivo do mesmo jeito, e listar verbos é
corrida perdida — e responde em três tons: **cala** quando o alvo não é
credencial ou o comando só lê nome (`ls`, `test`, `find`, `stat`, e os
subcomandos de git que só listam — `ls-files`, `status`, `check-ignore`);
**orienta** quando o comando lê conteúdo de credencial — a leitura passa, e
o modelo recebe por `additionalContext` onde o arquivo mora, `${VARIAVEL}`
no lugar do valor e o que fazer se ele já entrou no git; **veta** quando o
alvo é credencial e o comando grava história ou publica — publicação não se
desfaz. Dentro do `git`, quem decide é o **subcomando**, não o nome `git`:
o motivo é um falso positivo medido, uma sessão de diagnóstico inteira
barrada de perguntar `git ls-files` e `git status` sobre a gaveta —
comandos que não escrevem uma linha em lugar nenhum. Subcomando fora das
listas de leitura continua vetando: o conjunto que grava é aberto, e lista
fechada do lado errado vaza.

Ele cobre as **duas portas de leitura** da sessão: o shell e a ferramenta de
leitura direta do agente (`Read`). Antes, a mesma casa ensinava por uma
porta e murava a outra — um `deny` negava a gaveta `.credenciais/` inteira,
sem lição, e quem pagava era o script versionado que mora nela por
conveniência. Muro só é melhor que professor onde professor não existe: em
ferramenta que não roda gancho, o `deny` fica. Ele carrega o próprio teste:
`python .claude/hooks/orientar-credencial.py --testar` — e dois avaliadores
avulsos, `--avaliar '<comando>'` e `--avaliar-arquivo '<caminho>'`, que
repetem o julgamento sem executar nada.

Ele também é o **primeiro cliente do recibo da esteira**: cada orientação
vira recibo `segue` e cada veto um `para`, materializados por código
(`.agents/recibo/recibo.py`) em `tmp/recibos/orientacao-credencial/` — com
prova re-executável pelo `--avaliar`. O recibo nunca decide: se falhar, a
decisão do gancho sai igual.

Os limites dele, declarados:

- **Falar do assunto cala.** Mensagem entre aspas (`-m "explica o .env"`) e
  corpo de documento literal (`<<'FIM'`) são dados, não alvos. Sem isso o
  gancho morderia quem escreve o recibo dele — foi o que aconteceu com o veto
  de branch.
- **A mensagem que executa não passa.** Dentro de aspas duplas o `$(...)`
  ainda roda, então `-m "$(cat .env)"` leva a leitura para a história — e
  história é onde o veto continua.
- **Orientar não é aprovar.** A orientação viaja sem `permissionDecision`
  nenhum: um `allow` auto-aprovaria a chamada, e o fluxo de permissão da
  sessão fica como está (medido em 16/08/2026, claude 2.1.233).
- **Arquivo de exemplo entra junto**, porque o `deny` já o pega — duas
  proteções da mesma casa discordando é pior que uma orientando demais.
- **Ele não substitui o `deny` da ferramenta de leitura.** Gancho falha
  aberto; a regra de permissão é a rede de baixo. É sobreposição declarada,
  não descuido — e mudar esse eixo é a peça 2 do desenho, ainda por vir.

## Todo gancho nasce com teste

Um veto largo demais é desligado na primeira semana. Por isso o teste tem duas
listas, e a segunda é a que importa:

```python
BARRA = [
    ("a forma óbvia",          "git push --force origin main"),
    ("a que o glob não pega",  "git push origin +feature/x"),
    ("escondida depois de &&", "git status && git push --force origin x"),
    ("bandeira antes do verbo", "git -C /tmp push --force origin x"),
]

DEIXA_PASSAR = [
    ("push normal",            "git push origin feature/x"),
    ("nome que só parece",     "git push origin feature/forcado"),
    ("outro programa",         "docker push imagem:tag"),
]
```

Metade dos casos existe para provar que o gancho **não** atrapalha.

### O que não entra num teste

Fixture é onde dado sensível se esconde melhor — é a regra 13, em
[as regras da camada](regras-da-camada.md). Invente os nomes dos seus
testes. O que você digita todo dia é o que menos serve — é justamente o que
outra pessoa reconheceria.
