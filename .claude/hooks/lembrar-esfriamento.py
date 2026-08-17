"""Gancho Stop: lembra o esfriamento — uma vez por sessão, e só quando houve
trabalho de verdade.

O fechamento mais importante da sessão dependia de alguém lembrar de
invocá-lo — exatamente o que gancho existe para resolver. Este dispara no
fim de cada turno e quase sempre CALA: os portões são metade do valor
(lição do sistema estudado — sem eles, lembrete vira ruído e ruído ensina
a ignorar aviso).

Os portões, na ordem (qualquer um cala, saindo 0 sem imprimir):

1. `stop_hook_active` — o modelo já está continuando por causa de um gancho
   Stop; insistir seria laço.
2. Sem `session_id` — sem chave não há como garantir "uma vez por sessão".
3. `background_tasks`/`session_crons` não vazios — sessão pausada esperando
   trabalho de fundo não é sessão terminando.
4. Marca em `tmp/esfriamento-lembrado/<session_id>` — já lembrou nesta
   sessão.
5. `last_assistant_message` cita o esfriamento — já rodou, ou está rodando.
6. Transcript pequeno (< LIMIAR_BYTES) — sessão curta não precisa de
   fechamento cerimonial.
7. O transcript INTEIRO cita o esfriamento — o portão erra para o lado do
   silêncio de propósito (medido em 17/08/2026: o esfriamento rodou, a
   última resposta falava de outra coisa, e o lembrete saiu falso; sessão
   que só mencionou o assunto de passagem fica sem lembrete, e a skill
   continua sendo o caminho manual).
8. Poucos turnos de usuário (< LIMIAR_TURNOS) no transcript.
9. Nenhum uso de Edit/Write/Bash no transcript — sessão só de leitura e
   pergunta.

Passou por todos: grava a marca e devolve `additionalContext` (orientação,
não erro — `decision: block` prenderia quem só quer encerrar). O formato
interno do transcript não é contrato documentado; por isso os portões que o
leem falham ABERTOS — qualquer erro cala. A skill `esfriamento` continua
sendo o caminho em agente sem gancho.

Rode os testes com:  python .claude/hooks/lembrar-esfriamento.py --testar
"""

import json
import os
import sys
from pathlib import Path

LIMIAR_BYTES = 80_000
LIMIAR_TURNOS = 5
PASTA_MARCAS = "tmp/esfriamento-lembrado"

# As marcas se procuram no texto cru do transcript, nas duas grafias que o
# JSON pode ter (com e sem espaço após os dois-pontos).
FERRAMENTAS_DE_TRABALHO = ("Edit", "Write", "Bash")

LEMBRETE = (
    "A sessão fez trabalho de verdade e o esfriamento ainda não rodou. Se o "
    "trabalho terminou, feche o dia: rode a skill esfriamento (uma linha: "
    '"O trabalho terminou. Rode o esfriamento."). Se ainda não terminou, '
    "siga — este lembrete sai uma vez por sessão."
)


def raiz_do_repositorio() -> Path:
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(base) if base else Path(__file__).resolve().parents[2]


def _tem_marca(texto: str, chave: str, valor: str) -> bool:
    return f'"{chave}":"{valor}"' in texto or f'"{chave}": "{valor}"' in texto


def decisao(entrada: dict, raiz: Path) -> str:
    """'' para calar; o motivo curto quando é hora de lembrar.

    Só leitura — quem grava a marca é o main(), depois de decidir.
    """
    if entrada.get("stop_hook_active"):
        return ""
    sessao = entrada.get("session_id", "")
    if not sessao or "/" in sessao or "\\" in sessao:
        return ""
    if entrada.get("background_tasks") or entrada.get("session_crons"):
        return ""
    if (raiz / PASTA_MARCAS / sessao).exists():
        return ""
    ultima = entrada.get("last_assistant_message") or ""
    if "esfriamento" in ultima.lower():
        return ""
    try:
        transcript = Path(entrada.get("transcript_path", ""))
        if transcript.stat().st_size < LIMIAR_BYTES:
            return ""
        texto = transcript.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if "esfriamento" in texto.lower():
        return ""
    turnos = sum(1 for linha in texto.splitlines()
                 if _tem_marca(linha, "type", "user"))
    if turnos < LIMIAR_TURNOS:
        return ""
    if not any(_tem_marca(texto, "name", f) for f in FERRAMENTAS_DE_TRABALHO):
        return ""
    return "sessão de trabalho sem esfriamento"


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return 0
        raiz = raiz_do_repositorio()
        if not decisao(entrada, raiz):
            return 0
        marca = raiz / PASTA_MARCAS / entrada["session_id"]
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text("lembrado\n", encoding="utf-8")
    except Exception:
        return 0  # falha aberto: lembrete nunca prende a sessão

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": LEMBRETE,
    }}))
    return 0


# --- Testes -----------------------------------------------------------------
# Duas listas, e a que importa é a CALA: lembrete que dispara à toa é
# desligado na primeira semana.

def testar() -> int:
    import io
    import tempfile

    falhas = []

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(f"  {rotulo}")

    with tempfile.TemporaryDirectory(prefix="lembrar-teste-") as pasta:
        raiz = Path(pasta)

        def transcript(nome, tamanho, turnos, ferramenta, recheio_extra=""):
            linhas = ['{"type": "user", "message": "pedido"}'] * turnos
            if ferramenta:
                linhas.append(
                    f'{{"type": "assistant", "name": "{ferramenta}"}}')
            if recheio_extra:
                linhas.append(recheio_extra)
            recheio = '{"type": "assistant", "message": "' \
                      + "x" * 200 + '"}'
            while sum(len(linha) + 1 for linha in linhas) < tamanho:
                linhas.append(recheio)
            caminho = raiz / nome
            caminho.write_text("\n".join(linhas), encoding="utf-8")
            return str(caminho)

        trabalho = transcript("trabalho.jsonl", LIMIAR_BYTES + 1, 6, "Edit")
        so_leitura = transcript("leitura.jsonl", LIMIAR_BYTES + 1, 6, "")
        curto = transcript("curto.jsonl", 500, 6, "Edit")
        poucos = transcript("poucos.jsonl", LIMIAR_BYTES + 1, 2, "Edit")
        base = {"session_id": "s1", "transcript_path": trabalho}

        CALA = [
            ("laço: stop_hook_active", {**base, "stop_hook_active": True}),
            ("sem session_id", {"transcript_path": trabalho}),
            ("session_id com separador de caminho",
             {**base, "session_id": "../fuga"}),
            ("trabalho de fundo pendente",
             {**base, "background_tasks": [{"id": 1}]}),
            ("rotina agendada na sessão",
             {**base, "session_crons": [{"id": 1}]}),
            ("o esfriamento já apareceu na resposta",
             {**base, "last_assistant_message": "Rodei o ESFRIAMENTO."}),
            # O falso lembrete medido em 17/08/2026: o esfriamento rodou
            # turnos atrás e a última resposta falava de outra coisa.
            ("o esfriamento está no transcript, não na última resposta",
             {**base, "transcript_path": transcript(
                 "ja-esfriou.jsonl", LIMIAR_BYTES + 1, 6, "Edit",
                 recheio_extra='{"type": "assistant", "message": '
                               '"## Esfriamento — colhido"}')}),
            ("transcript pequeno", {**base, "transcript_path": curto}),
            ("poucos turnos de usuário",
             {**base, "transcript_path": poucos}),
            ("sessão só de leitura",
             {**base, "transcript_path": so_leitura}),
            ("transcript que não existe",
             {**base, "transcript_path": str(raiz / "nao-ha.jsonl")}),
        ]
        for rotulo, entrada in CALA:
            if decisao(entrada, raiz):
                falhas.append(f"  DEVIA CALAR e lembrou — {rotulo}")

        caso("DEVIA LEMBRAR: sessão de trabalho sem esfriamento",
             decisao(base, raiz) != "")

        # O ciclo inteiro pelo main(): lembra uma vez, e a marca cala a
        # segunda — mesmo payload, mesma sessão.
        guardado = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = pasta
        try:
            for rodada, esperado in (("primeira", True), ("segunda", False)):
                sys.stdin = io.StringIO(json.dumps(base))
                saida = io.StringIO()
                stdout = sys.stdout
                sys.stdout = saida
                try:
                    codigo = main()
                finally:
                    sys.stdout = stdout
                caso(f"main sai 0 na {rodada} chamada", codigo == 0)
                caso(f"{rodada} chamada {'lembra' if esperado else 'cala'}",
                     bool(saida.getvalue().strip()) == esperado)
                if esperado and saida.getvalue().strip():
                    corpo = json.loads(saida.getvalue())["hookSpecificOutput"]
                    caso("o lembrete é contexto de Stop, não erro",
                         corpo.get("hookEventName") == "Stop"
                         and "esfriamento" in corpo.get(
                             "additionalContext", ""))
            caso("a marca nasceu dentro de tmp/ (descartável)",
                 (raiz / PASTA_MARCAS / "s1").is_file())
        finally:
            sys.stdin = sys.__stdin__
            if guardado is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = guardado

        # Falha aberta: entrada quebrada cala e sai 0.
        sys.stdin = io.StringIO("{ nem json")
        saida = io.StringIO()
        stdout = sys.stdout
        sys.stdout = saida
        try:
            codigo = main()
        finally:
            sys.stdout = stdout
            sys.stdin = sys.__stdin__
        caso("entrada quebrada: cala e sai 0",
             codigo == 0 and not saida.getvalue().strip())

    total = len(CALA) + 8
    if falhas:
        print(f"FALHOU: {len(falhas)} casos")
        print("\n".join(falhas))
        return 1
    print(f"OK: {total} casos — {len(CALA)} calam, 1 lembra, e o ciclo "
          "(marca única, contexto de Stop, falha aberta) confere")
    return 0


if __name__ == "__main__":
    sys.exit(testar() if "--testar" in sys.argv else main())
