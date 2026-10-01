#!/usr/bin/env bash
CANDIDATOS="python3 python py"
CANDIDATOS_NO_WINDOWS="python py python3"
PERGUNTA='import sys; print(sys.version_info[0])'
VERSAO_QUE_SERVE=3
SAIDA_QUE_BARRA=2
NOME_DA_LEMBRANCA="atlas-interpretador-lembrado"

case "$OSTYPE" in
  cygwin*|msys*|win32*) ORDEM_DA_PLATAFORMA="$CANDIDATOS_NO_WINDOWS" ;;
  *) ORDEM_DA_PLATAFORMA="$CANDIDATOS" ;;
esac

pasta_privada() {
  if [ -n "$XDG_RUNTIME_DIR" ] && [ -d "$XDG_RUNTIME_DIR" ]; then
    printf '%s\n' "$XDG_RUNTIME_DIR"
  elif [ -n "$LOCALAPPDATA" ] && [ -d "$LOCALAPPDATA" ]; then
    printf '%s\n' "$LOCALAPPDATA"
  else
    return 1
  fi
}

if [ -n "$ATLAS_LEMBRANCA_DO_INTERPRETADOR" ]; then
  LEMBRANCA="$ATLAS_LEMBRANCA_DO_INTERPRETADOR"
elif pasta=$(pasta_privada); then
  LEMBRANCA="$pasta/$NOME_DA_LEMBRANCA"
else
  LEMBRANCA=""
fi

SEM_PYTHON="atlas: nenhum Python 3 respondeu ao lançador dos ganchos (tentei: $ORDEM_DA_PLATAFORMA). Nenhuma cerca roda; instale um Python 3 no PATH de quem abre o cliente e abra outra sessão"

escolher() {
  for nome in $ORDEM_DA_PLATAFORMA; do
    case " ${DESCARTADOS:-} " in *" $nome "*) continue ;; esac
    if [ "$("$nome" -c "$PERGUNTA" 2>/dev/null)" = "$VERSAO_QUE_SERVE" ]; then
      printf '%s\n' "$nome"
      return 0
    fi
  done
  return 1
}

nome_permitido() {
  case " $CANDIDATOS " in
    *" $1 "*) return 0 ;;
  esac
  return 1
}

lembrado() {
  [ -n "$LEMBRANCA" ] || return 1
  [ ! -L "$LEMBRANCA" ] || return 1
  [ -f "$LEMBRANCA" ] || return 1
  [ -O "$LEMBRANCA" ] || return 1
  local nome caminho
  {
    IFS= read -r nome || return 1
    IFS= read -r caminho || return 1
  } < "$LEMBRANCA"
  nome_permitido "$nome" || return 1
  [ -n "$caminho" ] && [ "$(command -v "$nome")" = "$caminho" ] || return 1
  printf '%s\n' "$nome"
}

lembrar() {
  [ -n "$LEMBRANCA" ] || return 0
  [ ! -L "$LEMBRANCA" ] || return 0
  local rascunho="$LEMBRANCA.$$"
  [ ! -e "$rascunho" ] && [ ! -L "$rascunho" ] || return 0
  (umask 077; set -C; printf '%s\n%s\n' "$1" "$(command -v "$1")" > "$rascunho") 2>/dev/null || return 0
  mv -f "$rascunho" "$LEMBRANCA" 2>/dev/null || rm -f "$rascunho" 2>/dev/null
}

if [ "$1" = "--testar" ]; then
  falhas=0
  casos=0
  banco=$(mktemp -d) || exit 1
  LEMBRANCA="$banco/lembrado"
  PASTA_DO_SHELL=${BASH%/*}

  rm -f "$LEMBRANCA"
  casos=$((casos + 1))
  if ! nome=$(escolher); then
    falhas=$((falhas + 1))
    printf 'FALHOU: %s\n' "$SEM_PYTHON"
  else
    lembrar "$nome"
    casos=$((casos + 1))
    if [ "$(lembrado)" != "$nome" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: a lembrança não devolveu %s\n' "$nome"
    fi

    printf 'nao-existe-este-python\n' > "$LEMBRANCA"
    casos=$((casos + 1))
    if lembrado >/dev/null 2>&1; then
      falhas=$((falhas + 1))
      printf 'FALHOU: lembrança apontando para nome que não existe foi aceita\n'
    fi

    : > "$LEMBRANCA"
    casos=$((casos + 1))
    if lembrado >/dev/null 2>&1; then
      falhas=$((falhas + 1))
      printf 'FALHOU: lembrança vazia foi aceita\n'
    fi

    impostor="$banco/impostor"
    printf 'echo IMPOSTOR-RODOU\n' > "$impostor"
    chmod +x "$impostor"
    printf '%s\n' "$impostor" > "$LEMBRANCA"
    casos=$((casos + 1))
    if lembrado >/dev/null 2>&1; then
      falhas=$((falhas + 1))
      printf 'FALHOU: lembrança com caminho de programa fora da lista foi aceita\n'
    fi
    casos=$((casos + 1))
    resposta=$(ATLAS_LEMBRANCA_DO_INTERPRETADOR="$LEMBRANCA" "$BASH" "$0" -c "print('python-de-verdade')" 2>/dev/null </dev/null)
    if [ "$resposta" != "python-de-verdade" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: com lembrança plantada o lançador respondeu "%s" em vez de rodar o Python\n' "$resposta"
    fi

    casos=$((casos + 1))
    if [ "$(sed -n '1p' "$LEMBRANCA")" != "$nome" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: a lembrança plantada não foi trocada pelo nome sondado (%s)\n' "$nome"
    fi

    alvo="$banco/alvo-do-link"
    printf '%s\n' "$nome" > "$alvo"
    rm -f "$LEMBRANCA"
    if ln -s "$alvo" "$LEMBRANCA" 2>/dev/null && [ -L "$LEMBRANCA" ]; then
      casos=$((casos + 1))
      if lembrado >/dev/null 2>&1; then
        falhas=$((falhas + 1))
        printf 'FALHOU: lembrança que é link simbólico foi aceita\n'
      fi
      casos=$((casos + 1))
      printf 'outro\n' > "$alvo"
      lembrar "$nome"
      if [ "$(sed -n '1p' "$alvo")" != "outro" ]; then
        falhas=$((falhas + 1))
        printf 'FALHOU: a escrita seguiu o link simbólico\n'
      fi
    fi
    rm -f "$LEMBRANCA"

    mkdir -p "$LEMBRANCA"
    casos=$((casos + 1))
    if lembrado >/dev/null 2>&1; then
      falhas=$((falhas + 1))
      printf 'FALHOU: lembrança que é pasta foi aceita\n'
    fi
    rmdir "$LEMBRANCA" 2>/dev/null

    casos=$((casos + 1))
    resposta=$(env -u ATLAS_LEMBRANCA_DO_INTERPRETADOR -u XDG_RUNTIME_DIR -u LOCALAPPDATA "$BASH" "$0" -c "print('sem-lembranca')" 2>/dev/null </dev/null)
    if [ "$resposta" != "sem-lembranca" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: sem pasta privada o lançador deveria sondar e rodar, respondeu "%s"\n' "$resposta"
    fi

    casos=$((casos + 1))
    fora=$(PATH="$PASTA_DO_SHELL" ATLAS_LEMBRANCA_DO_INTERPRETADOR="$banco/nao-usada" \
           "$BASH" "$0" -c "pass" 2>/dev/null </dev/null; printf '%s' "$?")
    if [ "$fora" != "$SAIDA_QUE_BARRA" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: sem Python o lançador saiu %s, e só %s barra a chamada\n' \
             "$fora" "$SAIDA_QUE_BARRA"
    fi
  fi

  real=$(command -v "$nome")
  mkdir -p "$banco/programas"
  catador="$banco/gancho.py"
  printf '%s\n' 'import sys' 'from pathlib import Path' 'sys.stdout.reconfigure(newline="\n")' 'registro = Path(sys.argv[1])' 'with registro.open("a", newline="\n") as arquivo: arquivo.write("rodou\n")' 'print(sys.flags.utf8_mode)' 'sys.stdout.write(sys.stdin.read())' 'sys.exit(int(sys.argv[2]))' > "$catador"

  conferir() {
    if ! "$@"; then
      falhas=$((falhas + 1))
      printf 'FALHOU: %s\n' "$caso"
    fi
  }

  preparar() {
    caso="$1"
    casos=$((casos + 1))
    rm -f "$banco/programas/python" "$banco/programas/python3" "$banco/programas/py" "$LEMBRANCA" "$banco/contagem" "$banco/sondas"
    entrada='entrada'
  }

  falso() {
    printf '#!%s\n%s\n' "$BASH" "$2" > "$banco/programas/$1"
    chmod +x "$banco/programas/$1"
  }

  verdadeiro() {
    printf -v programa 'if [ "$1" = -c ]; then printf "sonda\\n" >> %q; fi\nexec %q "$@"' "$banco/sondas" "$real"
    falso "$1" "$programa"
  }

  gravar() {
    printf '%s\n%s\n' "$1" "$banco/programas/$1" > "$LEMBRANCA"
  }

  chamar() {
    printf '%s' "$entrada" | PATH="$banco/programas:$PASTA_DO_SHELL" ATLAS_LEMBRANCA_DO_INTERPRETADOR="$LEMBRANCA" "$BASH" "$0" "$@" > "$banco/saida" 2> "$banco/erro"
    codigo=$?
    resposta=$(< "$banco/saida")
    erro=$(< "$banco/erro")
  }

  json_correto() {
    "$real" -X utf8 -c 'import json,sys; dado=json.load(open(sys.argv[1],encoding="utf-8")); mensagem="atlas: nenhum Python 3 respondeu"; evento=sys.argv[2]; cliente=sys.argv[3]; assert (dado["hookSpecificOutput"]["permissionDecision"] == "deny" and dado["hookSpecificOutput"]["permissionDecisionReason"].startswith(mensagem)) if cliente == "codex" and evento == "PreToolUse" else dado["systemMessage"].startswith(mensagem); assert evento != "SessionStart" or (dado["hookSpecificOutput"]["hookEventName"] == evento and dado["hookSpecificOutput"]["additionalContext"] == dado["systemMessage"])' "$banco/saida" "$1" "${2:-claude}" 2>/dev/null
  }

  preparar L1
  falso python 'exit 49'
  verdadeiro python3
  gravar python
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir test "$(sed -n '1p' "$LEMBRANCA")" = python3
  conferir test "$(< "$banco/contagem")" = rodou

  preparar L2
  verdadeiro python
  printf 'python\n/caminho/anterior\n' > "$LEMBRANCA"
  conferir test -z "$(PATH="$banco/programas:$PASTA_DO_SHELL" lembrado)"
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir test "$(sed -n '2p' "$LEMBRANCA")" = "$banco/programas/python"
  printf 'python\n' > "$LEMBRANCA"
  conferir test -z "$(PATH="$banco/programas:$PASTA_DO_SHELL" lembrado)"
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$(sed -n '2p' "$LEMBRANCA")" = "$banco/programas/python"

  preparar L3
  chamar --evento PreToolUse
  conferir test "$codigo" = 2
  conferir test -n "$erro"
  conferir test -z "$resposta"
  chamar --evento PreToolUse --cliente codex
  conferir test "$codigo" = 0
  conferir json_correto PreToolUse codex

  preparar L4
  chamar --evento SessionStart
  conferir test "$codigo" = 0
  conferir json_correto SessionStart

  preparar L5
  for evento_teste in Stop SubagentStop PostToolUseFailure PermissionDenied UserPromptSubmit PostToolUse Notification; do
    for cliente_teste in claude codex; do
      chamar --evento "$evento_teste" --cliente "$cliente_teste"
      conferir test "$codigo" = 0
      conferir json_correto "$evento_teste" "$cliente_teste"
    done
  done

  preparar L6
  chamar
  conferir test "$codigo" = 2
  conferir test -n "$erro"

  preparar L7
  entrada='{"hook_event_name":"PreToolUse","tool_input":{"texto":"\"hook_event_name\":\"Stop\""}}'
  chamar --evento PreToolUse
  conferir test "$codigo" = 2
  entrada='{"hook_event_name":"PreToolUse","texto":"PreToolUse"}'
  chamar --evento Stop
  conferir test "$codigo" = 0
  conferir json_correto Stop

  preparar L8
  PATH="$banco/programas:$PASTA_DO_SHELL" ATLAS_LEMBRANCA_DO_INTERPRETADOR="$LEMBRANCA" "$BASH" "$0" </dev/null > "$banco/saida" 2> "$banco/erro"
  conferir test "$?" = 2

  preparar L9
  verdadeiro python3
  entrada=$'ção ✓ 日本\n\n'
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir "$real" -X utf8 -c 'import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_bytes() == ("1\n"+sys.argv[2]).encode()' "$banco/saida" "$entrada"

  preparar L10
  verdadeiro python3
  gravar python3
  for esperado in 0 1 2; do
    rm -f "$banco/contagem" "$banco/sondas"
    chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" "$esperado"
    conferir test "$codigo" = "$esperado"
    conferir test "$(< "$banco/contagem")" = rodou
    if [ "$esperado" = 0 ]; then
      conferir test ! -e "$banco/sondas"
    else
      conferir test "$(< "$banco/sondas")" = sonda
    fi
  done
  falso python 'exit 1'
  gravar python
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir test "$(sed -n '1p' "$LEMBRANCA")" = python3

  preparar L11
  falso python 'exit 127'
  verdadeiro python3
  gravar python
  entrada=$'ção ✓ 日本\n\n'
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir test "$(< "$banco/contagem")" = rodou
  conferir "$real" -X utf8 -c 'import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_bytes() == ("1\n"+sys.argv[2]).encode()' "$banco/saida" "$entrada"

  preparar L12
  falso python 'exit 103'
  verdadeiro python3
  gravar python
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 0
  conferir test "$codigo" = 0
  conferir test "$(< "$banco/contagem")" = rodou
  rm -f "$banco/programas/python3"
  gravar python
  chamar --evento PreToolUse
  conferir test "$codigo" = 2

  preparar L13
  verdadeiro python3
  gravar python3
  chamar --evento PreToolUse -X utf8 "$catador" "$banco/contagem" 3
  conferir test "$codigo" = 3
  conferir test "$(< "$banco/contagem")" = rodou
  conferir test "$(< "$banco/sondas")" = sonda

  rm -rf "$banco" 2>/dev/null
  if [ "$falhas" -eq 0 ]; then
    printf 'OK: %s casos — o lançador escolhe, lembra em pasta privada, só aceita nome da lista, recusa link, pasta e impostor, e barra sem Python\n' "$casos"
    exit 0
  fi
  printf 'FALHOU: %s de %s casos\n' "$falhas" "$casos"
  exit 1
fi

evento=desconhecido
cliente=claude
if [ "$1" = --evento ] && [ "$#" -ge 2 ]; then
  evento="$2"
  shift 2
fi
if [ "$1" = --cliente ] && [ "$#" -ge 2 ]; then
  cliente="$2"
  shift 2
fi
entrada=""
IFS= read -r -d '' entrada || :
DESCARTADOS=""
nome=$(lembrado) || nome=""
while :; do
  if [ -z "$nome" ]; then
    nome=$(escolher) || break
    lembrar "$nome"
  fi
  printf '%s' "$entrada" | "$nome" "$@"
  codigo=$?
  case "$codigo" in 0) exit 0 ;; esac
  if [ "$("$nome" -c "$PERGUNTA" 2>/dev/null)" = "$VERSAO_QUE_SERVE" ]; then
    exit "$codigo"
  fi
  [ -n "$LEMBRANCA" ] && [ ! -L "$LEMBRANCA" ] && [ -f "$LEMBRANCA" ] && [ -O "$LEMBRANCA" ] && rm -f "$LEMBRANCA"
  DESCARTADOS="$DESCARTADOS $nome"
  nome=""
done

mensagem=${SEM_PYTHON//\\/\\\\}
mensagem=${mensagem//\"/\\\"}
case "$evento" in
  desconhecido)
    printf '%s\n' "$SEM_PYTHON" >&2
    exit "$SAIDA_QUE_BARRA"
    ;;
  PreToolUse)
    if [ "$cliente" = codex ]; then
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$mensagem"
    else
      printf '%s\n' "$SEM_PYTHON" >&2
      exit "$SAIDA_QUE_BARRA"
    fi
    ;;
  SessionStart)
    printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$mensagem" "$mensagem"
    ;;
  *) printf '{"systemMessage":"%s"}\n' "$mensagem" ;;
esac
exit 0
