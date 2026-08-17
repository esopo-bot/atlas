# Ganchos: a regra que roda sozinha

Gancho é um programa que o agente executa em pontos fixos da sessão. Não
pede licença e não depende de o modelo lembrar da regra.

## Regra de texto ou gancho?

| Você quer                                       | Use                      |
| ----------------------------------------------- | ------------------------ |
| Negar um comando que um padrão descreve inteiro | regra em `settings.json` |
| Decidir olhando o comando de verdade            | gancho                   |
| Injetar informação no começo da sessão          | gancho                   |
| Conferir alguma coisa depois de cada edição     | gancho                   |

O caso que decide: `git push origin +feature/x` é forçado e
`git push origin feature/x` não é — padrão de texto nenhum separa os dois.
O `deny` nega curto e sem lição; o gancho nega com o motivo junto.

## Onde se liga

No `settings.json`, por evento e por alvo:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          { "type": "command",
            "command": "python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/veto.py\"" }
        ]
      }
    ]
  }
}
```

- `type` é obrigatório; o `matcher` aceita nomes separados por `|`, `*` e
  nome de ferramenta MCP.
- `${CLAUDE_PROJECT_DIR}` entre aspas duplas — o cwd anda com cada `cd`, e
  gancho de caminho relativo trava a sessão inteira numa subpasta.
- Dentro do gancho, ache a raiz pelo mesmo caminho: a variável de ambiente,
  com fallback para a posição do próprio arquivo — nunca `Path.cwd()`.

## Os eventos que resolvem o dia a dia

| Evento                           | Dispara                     | Serve para                           |
| -------------------------------- | --------------------------- | ------------------------------------ |
| `PreToolUse`                     | antes de a ferramenta rodar | negar o que não pode acontecer       |
| `PostToolUse`                    | depois que ela rodou        | conferir o que acabou de mudar       |
| `SessionStart`                   | ao abrir a sessão           | injetar o que o agente precisa saber |
| `Stop`                           | ao fim de CADA turno        | devolver instrução ao modelo         |
| `SessionEnd`                     | ao encerrar a sessão        | limpar estado, registrar — sem falar com o modelo |
| `SubagentStart` / `SubagentStop` | em volta do subagente       | exigir registro do que ele fez       |

## O contrato

Recebe JSON no stdin; responde pelo que imprime. **Passar é sair `0`
calado.** `defer` é valor real do contrato, para integração headless
suspender e retomar a chamada — não o use como passagem.

Negar, num `PreToolUse` (escreva o motivo E a saída):

```python
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "o porquê, e qual é o caminho certo",
}}))
sys.exit(0)
```

Injetar contexto, num `SessionStart`: o mesmo envelope, com
`"additionalContext": "..."` no lugar da decisão. **`Stop` usa OUTRO
formato**: campos de topo `{"decision": "block", "reason": "..."}` —
`reason` obrigatório ao bloquear.

Mais três leis:

- O nome do programa é o basename, em minúsculas — `git`, `git.exe` e
  `/usr/bin/git` são o mesmo; e bandeira global (`git -C x push`) desloca o
  verbo.
- **Gancho falha aberto, de propósito**: erro sai `0`. Se o gancho não
  subir, não há proteção — a regra de texto fica no `settings.json` como
  rede de baixo.
- Todo gancho nasce com `--testar` e duas listas: a que barra E a que deixa
  passar — metade dos casos prova que ele não atrapalha. Invente os nomes
  das fixtures (regra 13): o que você digita todo dia é o que um colega
  reconheceria.

## Os ganchos que a camada traz

| Gancho                      | Evento         | O que faz                                                       |
| --------------------------- | -------------- | --------------------------------------------------------------- |
| `injetar-qualidade.py`      | `SessionStart` | entrega o padrão de código, que skill nenhuma dispara           |
| `conferir-mcp.py`           | `SessionStart` | acusa declaração de MCP apontando para arquivo que não existe   |
| `conferir-ambiente.py`      | `SessionStart` | acusa o que a máquina não tem e a casa declara precisar         |
| `vetar-branch-protegida.py` | `PreToolUse`   | recusa apagar, renomear e forçar branch de longa duração        |
| `orientar-credencial.py`    | `PreToolUse`   | lição curta ao ler credencial; veta só o que grava história ou publica |
| `lembrar-esfriamento.py`    | `Stop`         | lembra o esfriamento — uma vez por sessão, só quando houve trabalho |

Cada um carrega o próprio teste: `python .claude/hooks/<nome>.py --testar`.

- O veto de branch é a regra 12 virando trava; os nomes vêm de
  `.claude/branches-protegidas.txt` — **seu**, nunca reescrito. Push normal
  para branch protegida passa.
- O `conferir-ambiente.py` lê `${VAR}` do `.mcp.json` e o `ambiente.txt` da
  raiz (**seu**) — nomes e existência, nunca valores. O porquê:
  [o estado que não viaja](estado-que-nao-viaja.md).
- O professor de credencial é a regra 8 em código, nas duas portas de
  leitura (shell e `Read`):

  | Resposta | Quando |
  | --- | --- |
  | **cala** | o alvo não é credencial, ou o comando só lê nome (`ls`, `test`, `stat`, `git status`, `git ls-files`…) |
  | **lição de uma linha** | o comando lê conteúdo de credencial — `${VARIAVEL}` no rastreado; tire de vista ao terminar |
  | **veta** | o alvo é credencial e o comando grava história ou publica (`git`/`gh`; dentro do git, decide o subcomando) |

- Mensagem entre aspas e documento literal são dados — mas `$(...)` dentro
  de aspas duplas executa, e aí o veto fica. Avaliadores avulsos:
  `--avaliar '<comando>'` e `--avaliar-arquivo '<caminho>'`. Ele não vê
  imagem: print com segredo entra sem passar por gancho nenhum.
- Cada orientação/veto do professor vira recibo em
  `tmp/recibos/orientacao-credencial/` (`.agents/recibo/`); o recibo nunca
  decide — falha dele não muda a resposta.
- O lembrete de esfriamento quase sempre cala, e é desenho: trava
  anti-laço (`stop_hook_active`), marca de uma vez por sessão em `tmp/`,
  e portões de trivialidade — transcript pequeno, poucos turnos, nenhum
  Edit/Write/Bash, trabalho de fundo pendente. Lembrete é orientação
  (`additionalContext`), nunca erro; os portões falham abertos. A skill
  `esfriamento` segue sendo o caminho em agente sem gancho.
