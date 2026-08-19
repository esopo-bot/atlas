# Ganchos: a regra que roda sozinha

Gancho é um programa que o agente executa em pontos fixos da sessão. Não pede
licença e não depende de o modelo lembrar da regra.

## Regra de texto ou gancho?

| Você quer                                       | Use                      |
| ----------------------------------------------- | ------------------------ |
| Negar um comando que um padrão descreve inteiro | regra em `settings.json` |
| Decidir olhando o comando de verdade            | gancho                   |
| Injetar informação no começo da sessão          | gancho                   |
| Verificar alguma coisa depois de cada edição     | gancho                   |

O caso que decide: `git push origin +feature/x` é forçado e
`git push origin feature/x` não é — padrão de texto nenhum separa os dois. O
`deny` nega curto e sem lição; o gancho nega com o motivo junto.

## Onde se liga

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

- `type` é obrigatório; o `matcher` aceita nomes separados por `|`, `*` e nome
  de ferramenta MCP.
- `${CLAUDE_PROJECT_DIR}` **entre aspas duplas** — o cwd anda com cada `cd`, e
  gancho de caminho relativo trava a sessão numa subpasta.
- Dentro do gancho, ache a raiz pela variável de ambiente, com fallback para a
  posição do próprio arquivo — nunca `Path.cwd()`.

## Os eventos

| Evento                           | Dispara                     | Serve para                                        |
| -------------------------------- | --------------------------- | ------------------------------------------------- |
| `PreToolUse`                     | antes de a ferramenta rodar | negar o que não pode acontecer                    |
| `PostToolUse`                    | depois que ela rodou        | verificar o que acabou de mudar                    |
| `SessionStart`                   | ao abrir a sessão           | injetar o que o agente precisa saber              |
| `Stop`                           | ao fim de CADA turno        | devolver instrução ao modelo                      |
| `SessionEnd`                     | ao encerrar                 | limpar estado, registrar — sem falar com o modelo |
| `SubagentStart` / `SubagentStop` | em volta do subagente       | exigir registro do que ele fez                    |

## O contrato

Recebe JSON no stdin; responde pelo que imprime. **Passar é sair `0` calado.**
`defer` é valor real, para integração headless suspender e retomar a chamada —
não o use como passagem.

```python
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "o porquê, e qual é o caminho certo",
}}))
sys.exit(0)
```

`SessionStart` usa o mesmo envelope com `"additionalContext": "..."` no lugar
da decisão. **`Stop` usa OUTRO formato**: campos de topo
`{"decision": "block", "reason": "..."}`, com `reason` obrigatório ao bloquear.

Três leis:

- O nome do programa é o basename, em minúsculas — `git`, `git.exe` e
  `/usr/bin/git` são o mesmo; bandeira global (`git -C x push`) desloca o verbo.
- **Gancho falha aberto, de propósito**: erro sai `0`. Se ele não subir, não há
  proteção — a regra de texto fica no `settings.json` como rede de baixo.
- Todo gancho nasce com `--testar` e **duas** listas: a que barra e a que deixa
  passar — metade dos casos prova que ele não atrapalha.

## Os ganchos que a camada traz

| Gancho                      | Evento         | O que faz                                                              |
| --------------------------- | -------------- | ---------------------------------------------------------------------- |
| `injetar-qualidade.py`      | `SessionStart` | entrega o padrão de código, que skill nenhuma dispara                  |
| `verificar-mcp.py`           | `SessionStart` | acusa declaração de MCP apontando para arquivo que não existe          |
| `verificar-ambiente.py`      | `SessionStart` | acusa o que a máquina não tem e o repositório declara precisar  |
| `vetar-branch-protegida.py` | `PreToolUse`   | recusa o destrutivo em branch de longa duração, e o que o repositório não autorizou |
| `orientar-credencial.py`    | `PreToolUse`   | lição curta ao ler credencial; veta só o que grava história ou publica |
| `vetar-conhecimento-em-codigo.py` | `PreToolUse` | recusa nota nascendo em pasta de código; passa dentro de repositório |
| `lembrar-esfriamento.py`    | `Stop`         | lembra o esfriamento — uma vez por sessão, só quando houve trabalho    |

Todo gancho que **decide** carrega o próprio teste: `python .claude/hooks/<nome>.py --testar`. O `injetar-qualidade.py` não decide nada — só entrega texto na abertura da sessão — e por isso não tem um.

- **O que aciona automação se declara** (regra 9). O gancho lê
  `autorizacoes` de `nucleo/configuracao.json` — `commit`, `push`,
  `publicar` — e o padrão é **não**: ausente, ilegível ou fora do molde,
  nega. Antes disso, `git commit`, `git push origin main`, `gh pr create`,
  `gh pr merge` e `gh release create` passavam **todos** calados, e o
  silêncio era ausência de regra, não permissão. Autorização vale para o
  trabalho normal e **nunca** para o destrutivo: força em branch protegida
  continua negada mesmo com tudo ligado.

- **Conhecimento em pasta de código** tem o `.git` como fronteira: nota
  nascendo solta no diretório declarado é barrada; dentro de um repositório
  clonado ali, README e docs passam — o fluxo de revisão dele é que julga. A
  lista sai de `diretorios_so_codigo`, em `nucleo/executor.json`; **sem ela,
  tudo passa**. Duas famílias de matcher, porque só as ferramentas de escrita
  deixariam a porta do shell aberta. Fora das ferramentas do agente — um
  editor aberto à mão — nada impede, e isso é limite declarado, não promessa.

- **Branch protegida** é a regra 12 virando trava. Os nomes vêm de
  `.claude/branches-protegidas.txt` — **seu**, nunca reescrito. Branch nova
  passa sempre; commit e push seguem o que `autorizacoes` declara (abaixo).
- **Ambiente** lê `${VAR}` do `.mcp.json` e o `nucleo/ambiente.json` (**seu**)
  — nomes e existência, nunca valores. O porquê:
  [o estado que não viaja](estado-que-nao-viaja.md).
- **Credencial** é a regra 8 em código, nas duas portas de leitura (shell e
  `Read`):

  | Resposta | Quando |
  | --- | --- |
  | **cala** | o alvo não é credencial, ou o comando só lê nome (`ls`, `test`, `stat`, `git status`…) |
  | **lição** | o comando lê conteúdo — `${VARIAVEL}` no rastreado; tire de vista ao terminar |
  | **veta** | alvo é credencial e o comando grava história ou publica (`git`/`gh`; dentro do git, decide o subcomando) |

  Aspas e documento literal são dados, mas `$(...)` dentro de aspas duplas
  executa e aí o veto fica. Avulso: `--avaliar '<comando>'` e
  `--avaliar-arquivo '<caminho>'`. **Ele não vê imagem**: print com segredo
  entra sem passar por gancho nenhum. Cada decisão vira evidência em
  `tmp/evidencias/`, e a evidência nunca decide — falha dele não muda a resposta.
- **Esfriamento** quase sempre cala, e é desenho: trava anti-laço
  (`stop_hook_active`), marca de uma vez por sessão em `tmp/`, e filtros de
  trivialidade (transcript pequeno, poucos turnos, nenhum Edit/Write/Bash,
  trabalho de fundo pendente). É orientação, nunca erro, e os filtros falham
  abertos. Sem gancho, o caminho é a skill `esfriamento`.
