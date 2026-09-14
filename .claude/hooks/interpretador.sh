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

SEM_PYTHON="atlas: nenhum Python 3 respondeu ao lançador dos ganchos — tentei: $ORDEM_DA_PLATAFORMA. As cercas não rodam nesta máquina, então esta chamada fica BARRADA: cerca que não roda não deixa passar."

escolher() {
  for nome in $ORDEM_DA_PLATAFORMA; do
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
  local nome
  read -r nome < "$LEMBRANCA" || return 1
  nome_permitido "$nome" || return 1
  command -v "$nome" >/dev/null 2>&1 || return 1
  printf '%s\n' "$nome"
}

lembrar() {
  [ -n "$LEMBRANCA" ] || return 0
  [ ! -L "$LEMBRANCA" ] || return 0
  local rascunho="$LEMBRANCA.$$"
  printf '%s\n' "$1" > "$rascunho" 2>/dev/null || return 0
  mv -f "$rascunho" "$LEMBRANCA" 2>/dev/null || rm -f "$rascunho" 2>/dev/null
}

if [ "$1" = "--testar" ]; then
  falhas=0
  casos=0
  banco=$(mktemp -d 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
  LEMBRANCA="$banco/lembrado"
  PASTA_DO_SHELL=$(dirname "$BASH")

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
    resposta=$(ATLAS_LEMBRANCA_DO_INTERPRETADOR="$LEMBRANCA" "$BASH" "$0" -c "print('python-de-verdade')" 2>/dev/null)
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
    resposta=$(env -u ATLAS_LEMBRANCA_DO_INTERPRETADOR -u XDG_RUNTIME_DIR -u LOCALAPPDATA "$BASH" "$0" -c "print('sem-lembranca')" 2>/dev/null)
    if [ "$resposta" != "sem-lembranca" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: sem pasta privada o lançador deveria sondar e rodar, respondeu "%s"\n' "$resposta"
    fi

    casos=$((casos + 1))
    fora=$(PATH="$PASTA_DO_SHELL" ATLAS_LEMBRANCA_DO_INTERPRETADOR="$banco/nao-usada" \
           "$BASH" "$0" -c "pass" 2>/dev/null; printf '%s' "$?")
    if [ "$fora" != "$SAIDA_QUE_BARRA" ]; then
      falhas=$((falhas + 1))
      printf 'FALHOU: sem Python o lançador saiu %s, e só %s barra a chamada\n' \
             "$fora" "$SAIDA_QUE_BARRA"
    fi
  fi

  rm -rf "$banco" 2>/dev/null
  if [ "$falhas" -eq 0 ]; then
    printf 'OK: %s casos — o lançador escolhe, lembra em pasta privada, só aceita nome da lista, recusa link, pasta e impostor, e barra sem Python\n' "$casos"
    exit 0
  fi
  printf 'FALHOU: %s de %s casos\n' "$falhas" "$casos"
  exit 1
fi

if nome=$(lembrado); then
  exec "$nome" "$@"
fi

if nome=$(escolher); then
  lembrar "$nome"
  exec "$nome" "$@"
fi
printf '%s\n' "$SEM_PYTHON" >&2
exit "$SAIDA_QUE_BARRA"
