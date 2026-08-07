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
arquivo não passam por esse gancho — corrija o `settings.json` por elas. Em
um dos testes a configuração recarregou sozinha no meio da sessão e
destravou; não conte com isso em toda ferramenta.

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
| `vetar-branch-protegida.py`  | `PreToolUse`   | recusa apagar, renomear e forçar branch de longa duração |

O `conferir-mcp.py` existe porque servidor MCP com caminho morto não sobe e
não avisa — some da lista de ferramentas em silêncio. O detalhe está na
página de MCP. Ele carrega o próprio teste:
`python .claude/hooks/conferir-mcp.py --testar`.

O veto de branch é a regra 12 virando trava. Os nomes protegidos vêm de
`.claude/branches-protegidas.txt` — um por linha, **e esse arquivo é seu**: a
atualização traz o conserto do código e nunca reescreve a sua lista.

Ele carrega o próprio teste:

```bash
python .claude/hooks/vetar-branch-protegida.py --testar
```

E tem um limite declarado: **push normal para branch protegida passa.** Quem
decide isso é a regra 9 e o perfil do repositório. O gancho cuida do
destrutivo — apagar, renomear, reescrever — porque veto largo demais é
desligado na primeira semana.

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
