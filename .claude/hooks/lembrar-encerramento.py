import json
import os
import sys
from pathlib import Path

LIMIAR_BYTES = 80_000
LIMIAR_TURNOS = 5
PASTA_MARCAS = "tmp/encerramento-lembrado"
CONTEUDO_DA_MARCA = "lembrado\n"

FERRAMENTAS_DE_TRABALHO = ("Edit", "Write", "Bash")
CHAVE_DO_TIPO = "type"
TIPO_DE_TURNO_DE_USUARIO = "user"
CHAVE_DO_NOME = "name"
PALAVRA_DO_ENCERRAMENTO = "encerramento-de-sessao"
SEPARADORES_DE_CAMINHO = ("/", "\\")

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_DE_PARADA = "Stop"
BANDEIRA_DE_TESTE = "--testar"
NAO_LEMBRA = ""
MOTIVO_DE_LEMBRAR = "sessão de trabalho sem encerramento"
SILENCIO = 0
FALHA_ABERTO = 0
LEMBRETE_ENTREGUE = 0

LEMBRETE = (
    "A sessão fez trabalho de verdade e o encerramento ainda não rodou. Se o "
    "trabalho terminou, feche o dia: rode a skill encerramento-de-sessao (uma linha: "
    '"O trabalho terminou. Rode o encerramento-de-sessao."). Se ainda não terminou, '
    "siga — este lembrete sai uma vez por sessão."
)

FALHA_DE_CASO = "  {}"
FALHA_DEVIA_CALAR = "  DEVIA CALAR e lembrou — {}"
ROTULO_MAIN_SAI_ZERO = "main sai 0 na {} chamada"
ROTULO_DA_RODADA = "{} chamada {}"
PALAVRA_LEMBRA = "lembra"
PALAVRA_CALA = "cala"
RESUMO_FALHOU = "FALHOU: {} casos"
RESUMO_OK = ("OK: {} casos — {} calam, 1 lembra, e o ciclo (marca única, "
             "contexto de Stop, falha aberta) bate")


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def tem_par_json(texto: str, chave: str, valor: str) -> bool:
    return f'"{chave}":"{valor}"' in texto or f'"{chave}": "{valor}"' in texto


def cala_pelo_que_o_pedido_diz(entrada: dict, raiz: Path) -> bool:
    esta_num_laco_de_gancho_stop = entrada.get("stop_hook_active")
    if esta_num_laco_de_gancho_stop:
        return True

    sessao = entrada.get("session_id", "")
    sem_chave_para_marcar_uma_vez_por_sessao = (
        not sessao or any(s in sessao for s in SEPARADORES_DE_CAMINHO))
    if sem_chave_para_marcar_uma_vez_por_sessao:
        return True

    espera_trabalho_de_fundo = (entrada.get("background_tasks")
                                or entrada.get("session_crons"))
    if espera_trabalho_de_fundo:
        return True

    ja_lembrou_nesta_sessao = (raiz / PASTA_MARCAS / sessao).exists()
    if ja_lembrou_nesta_sessao:
        return True

    ultima_resposta = entrada.get("last_assistant_message") or ""
    return PALAVRA_DO_ENCERRAMENTO in ultima_resposta.lower()


def cala_pelo_que_o_transcript_mostra(entrada: dict) -> bool:
    try:
        transcript = Path(entrada.get("transcript_path", ""))
        sessao_curta_demais = transcript.stat().st_size < LIMIAR_BYTES
        if sessao_curta_demais:
            return True
        texto = transcript.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True

    o_encerramento_aparece_em_algum_turno = (
        PALAVRA_DO_ENCERRAMENTO in texto.lower())
    if o_encerramento_aparece_em_algum_turno:
        return True

    turnos_de_usuario = sum(
        1 for linha in texto.splitlines()
        if tem_par_json(linha, CHAVE_DO_TIPO, TIPO_DE_TURNO_DE_USUARIO))
    if turnos_de_usuario < LIMIAR_TURNOS:
        return True

    houve_ferramenta_de_trabalho = any(
        tem_par_json(texto, CHAVE_DO_NOME, ferramenta)
        for ferramenta in FERRAMENTAS_DE_TRABALHO)
    return not houve_ferramenta_de_trabalho


def decisao(entrada: dict, raiz: Path) -> str:
    if cala_pelo_que_o_pedido_diz(entrada, raiz):
        return NAO_LEMBRA
    if cala_pelo_que_o_transcript_mostra(entrada):
        return NAO_LEMBRA
    return MOTIVO_DE_LEMBRAR


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return SILENCIO
        raiz = raiz_do_projeto_nunca_o_cwd()
        if not decisao(entrada, raiz):
            return SILENCIO
        marca = raiz / PASTA_MARCAS / entrada["session_id"]
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(CONTEUDO_DA_MARCA, encoding="utf-8")
    except Exception:
        return FALHA_ABERTO

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_DE_PARADA,
        "additionalContext": LEMBRETE,
    }}))
    return LEMBRETE_ENTREGUE


def testar() -> int:
    import io
    import tempfile

    falhas = []

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(FALHA_DE_CASO.format(rotulo))

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
            ("o encerramento já apareceu na resposta",
             {**base, "last_assistant_message":
              "Rodei o ENCERRAMENTO-DE-SESSAO."}),
            ("o encerramento está no transcript, não na última resposta",
             {**base, "transcript_path": transcript(
                 "ja-esfriou.jsonl", LIMIAR_BYTES + 1, 6, "Edit",
                 recheio_extra='{"type": "assistant", "message": '
                               '"## encerramento-de-sessao — colhido"}')}),
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
                falhas.append(FALHA_DEVIA_CALAR.format(rotulo))

        caso("DEVIA LEMBRAR: sessão de trabalho sem encerramento",
             decisao(base, raiz) != NAO_LEMBRA)

        guardado = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
        os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = pasta
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
                caso(ROTULO_MAIN_SAI_ZERO.format(rodada), codigo == 0)
                caso(ROTULO_DA_RODADA.format(
                        rodada, PALAVRA_LEMBRA if esperado else PALAVRA_CALA),
                     bool(saida.getvalue().strip()) == esperado)
                if esperado and saida.getvalue().strip():
                    corpo = json.loads(saida.getvalue())["hookSpecificOutput"]
                    caso("o lembrete é contexto de Stop, não erro",
                         corpo.get("hookEventName") == EVENTO_DE_PARADA
                         and PALAVRA_DO_ENCERRAMENTO in corpo.get(
                             "additionalContext", ""))
            caso("a marca nasceu dentro de tmp/ (descartável)",
                 (raiz / PASTA_MARCAS / "s1").is_file())
        finally:
            sys.stdin = sys.__stdin__
            if guardado is None:
                os.environ.pop(VARIAVEL_DA_RAIZ_DO_PROJETO, None)
            else:
                os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = guardado

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
        print(RESUMO_FALHOU.format(len(falhas)))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(CALA)))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
