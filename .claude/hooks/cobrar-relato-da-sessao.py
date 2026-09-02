import json
import os
import sys
from pathlib import Path

LIMIAR_BYTES = 80_000
LIMIAR_TURNOS = 5
PASTA_MARCAS = "tmp/relato-cobrado"
CONTEUDO_DA_MARCA = "cobrado\n"

INSTRUMENTO_DO_RELATO = ".agents/entrega/entrega.py"
PROVA_DE_QUE_RELATOU = "entrega relatada na issue"
FERRAMENTAS_DE_TRABALHO = ("Edit", "Write", "NotebookEdit")
CHAVE_DO_TIPO = "type"
TIPO_DE_TURNO_DE_USUARIO = "user"
CHAVE_DO_NOME = "name"
SEPARADORES_DE_CAMINHO = ("/", "\\")

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_DE_PARADA = "Stop"
BANDEIRA_DE_TESTE = "--testar"
NAO_COBRA = ""
MOTIVO_DE_COBRAR = "sessão com trabalho e sem relato de entrega"
SILENCIO = 0
FALHA_ABERTO = 0
COBRANCA_ENTREGUE = 0

COBRANCA = (
    "A sessão escreveu arquivo e não deixou relato de entrega em issue "
    "nenhuma. Sem ele o dono não tem como ver o que foi feito nem o que "
    "ficou para ele — e número de issue solto, sem link, obriga a "
    "garimpar. Poste antes de fechar:\n\n"
    "  python3 {instrumento} --issue <n> \\\n"
    "    --pedido \"<o pedido do dono, colado>\" \\\n"
    "    --executado \"<um passo>\" \\\n"
    "    --entregue \"<o que|link>\" \\\n"
    "    --seu \"<o que espera por ele|link>\"\n\n"
    "Item entregue e item que fica para o dono levam LINK — o instrumento "
    "recusa sem. Havendo `--seu`, ele etiqueta a issue e move o cartão. "
    "Use `--ensaio` para ver antes de postar. Esta cobrança sai uma vez por "
    "sessão."
)

FALHA_DE_CASO = "  {}"
FALHA_DEVIA_CALAR = "  DEVIA CALAR e cobrou — {}"
RESUMO_FALHOU = "FALHOU: {} casos"
RESUMO_OK = ("OK: {} casos — {} calam, 1 cobra, e o contrato com o "
             "instrumento bate")


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def tem_par_json(texto: str, chave: str, valor: str) -> bool:
    return f'"{chave}":"{valor}"' in texto or f'"{chave}": "{valor}"' in texto


def nao_cobra_pelo_estado_da_sessao(entrada: dict, raiz: Path) -> bool:
    if entrada.get("stop_hook_active"):
        return True

    sessao = entrada.get("session_id", "")
    sem_chave_para_marcar_uma_vez_por_sessao = (
        not sessao or any(s in sessao for s in SEPARADORES_DE_CAMINHO))
    if sem_chave_para_marcar_uma_vez_por_sessao:
        return True

    if entrada.get("background_tasks") or entrada.get("session_crons"):
        return True

    return (raiz / PASTA_MARCAS / sessao).exists()


def nao_cobra_pelo_que_a_sessao_fez(entrada: dict) -> bool:
    try:
        transcript = Path(entrada.get("transcript_path", ""))
        if transcript.stat().st_size < LIMIAR_BYTES:
            return True
        texto = transcript.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True

    if PROVA_DE_QUE_RELATOU in texto:
        return True

    turnos_de_usuario = sum(
        1 for linha in texto.splitlines()
        if tem_par_json(linha, CHAVE_DO_TIPO, TIPO_DE_TURNO_DE_USUARIO))
    if turnos_de_usuario < LIMIAR_TURNOS:
        return True

    escreveu_arquivo = any(
        tem_par_json(texto, CHAVE_DO_NOME, ferramenta)
        for ferramenta in FERRAMENTAS_DE_TRABALHO)
    return not escreveu_arquivo


def decisao(entrada: dict, raiz: Path) -> str:
    if nao_cobra_pelo_estado_da_sessao(entrada, raiz):
        return NAO_COBRA
    if nao_cobra_pelo_que_a_sessao_fez(entrada):
        return NAO_COBRA
    return MOTIVO_DE_COBRAR


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
        "additionalContext": COBRANCA.format(
            instrumento=INSTRUMENTO_DO_RELATO),
    }}))
    return COBRANCA_ENTREGUE


def testar() -> int:
    import io
    import tempfile

    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(FALHA_DE_CASO.format(nome))

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)

        def transcript(nome: str, tamanho: int, turnos: int,
                       ferramenta: str = "Edit", extra: str = "") -> str:
            alvo = raiz / nome
            linhas = [json.dumps({"type": "user", "message": "oi"})
                      for _ in range(turnos)]
            linhas.append(json.dumps({"name": ferramenta}))
            if extra:
                linhas.append(extra)
            corpo = "\n".join(linhas)
            corpo += "\n" + "x" * max(0, tamanho - len(corpo))
            alvo.write_text(corpo, encoding="utf-8")
            return str(alvo)

        cheio = transcript("cheio.jsonl", LIMIAR_BYTES + 1, LIMIAR_TURNOS + 1)
        base = {"session_id": "sessao-1", "transcript_path": cheio}

        caso("DEVIA COBRAR: sessão que escreveu arquivo e não relatou",
             decisao(base, raiz) == MOTIVO_DE_COBRAR)

        calam = [
            ("laço do próprio gancho", {**base, "stop_hook_active": True}),
            ("sem identidade de sessão", {**base, "session_id": ""}),
            ("identidade que sobe de pasta",
             {**base, "session_id": "../fuga"}),
            ("trabalho de fundo pendente",
             {**base, "background_tasks": [{"id": 1}]}),
            ("rotina agendada na sessão",
             {**base, "session_crons": [{"id": 1}]}),
            ("o relato já foi postado nesta sessão",
             {**base, "transcript_path": transcript(
                 "relatou.jsonl", LIMIAR_BYTES + 1, LIMIAR_TURNOS + 1,
                 extra=json.dumps({"content": f"{PROVA_DE_QUE_RELATOU} 272"}))}),
            ("transcript pequeno demais para ter havido trabalho",
             {**base, "transcript_path": transcript(
                 "curto.jsonl", 10, LIMIAR_TURNOS + 1)}),
            ("poucos turnos de usuário",
             {**base, "transcript_path": transcript(
                 "poucos.jsonl", LIMIAR_BYTES + 1, 1)}),
            ("sessão que só leu, sem escrever arquivo",
             {**base, "transcript_path": transcript(
                 "so-leu.jsonl", LIMIAR_BYTES + 1, LIMIAR_TURNOS + 1,
                 ferramenta="Read")}),
            ("transcript que não existe", {**base,
                                           "transcript_path": "/nao/existe"}),
        ]
        for nome, entrada in calam:
            caso(FALHA_DEVIA_CALAR.format(nome),
                 decisao(entrada, raiz) == NAO_COBRA)

        guardado = sys.stdin
        try:
            sys.stdin = io.StringIO(json.dumps(base))
            os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = str(raiz)
            primeira = main()
            sys.stdin = io.StringIO(json.dumps(base))
            segunda_calada = decisao(base, raiz) == NAO_COBRA
        finally:
            sys.stdin = guardado
            os.environ.pop(VARIAVEL_DA_RAIZ_DO_PROJETO, None)
        caso("a cobrança sai zero — Stop que sai diferente de zero atrapalha",
             primeira == COBRANCA_ENTREGUE)
        caso("marca única: cobra uma vez por sessão e depois cala",
             (raiz / PASTA_MARCAS / "sessao-1").exists() and segunda_calada)

        guardado = sys.stdin
        try:
            sys.stdin = io.StringIO("[1, 2]")
            com_lista = main()
            sys.stdin = io.StringIO("nao e json")
            com_lixo = main()
        finally:
            sys.stdin = guardado
        caso("entrada que não é objeto sai calada, sem derrubar a sessão",
             com_lista == SILENCIO and com_lixo == FALHA_ABERTO)

        instrumento = (raiz_do_projeto_nunca_o_cwd() / INSTRUMENTO_DO_RELATO)
        try:
            fonte = instrumento.read_text(encoding="utf-8")
        except OSError:
            fonte = ""
        caso("o instrumento que a cobrança manda rodar existe onde ela diz",
             bool(fonte))
        caso("a frase que prova o relato é a que o instrumento imprime — "
             "senão a cobrança nunca cala e vira ruído toda sessão",
             PROVA_DE_QUE_RELATOU in fonte)

    if falhou:
        print(RESUMO_FALHOU.format(passou + falhou))
        return 1
    print(RESUMO_OK.format(passou + falhou, len(calam)))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv[1:] else main())
