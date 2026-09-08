#!/usr/bin/env bash
CANDIDATOS="python3 python py"
PERGUNTA='import sys; print(sys.version_info[0])'
VERSAO_QUE_SERVE=3
SEM_PYTHON="atlas: nenhum Python 3 respondeu ao lançador dos ganchos — tentei: $CANDIDATOS. As cercas não rodam nesta máquina."

escolher() {
  for nome in $CANDIDATOS; do
    if [ "$("$nome" -c "$PERGUNTA" 2>/dev/null)" = "$VERSAO_QUE_SERVE" ]; then
      printf '%s\n' "$nome"
      return 0
    fi
  done
  return 1
}

if [ "$1" = "--testar" ]; then
  if nome=$(escolher); then
    printf 'OK: 1 caso — o lançador escolhe %s por execução\n' "$nome"
    exit 0
  fi
  printf 'FALHOU: 1 caso — %s\n' "$SEM_PYTHON"
  exit 1
fi

if nome=$(escolher); then
  exec "$nome" "$@"
fi
printf '%s\n' "$SEM_PYTHON" >&2
exit 1
