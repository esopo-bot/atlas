import json
import os
import socket
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
ONDE_O_MODULO_PODE_ESTAR = (
    ".agents/indice/docker-compose.yml",
    "modulos/indice/.agents/indice/docker-compose.yml",
)

PECAS = (
    ("o banco de vetores", "INDICE_PORTA_MILVUS", 19530),
    ("quem gera os vetores", "INDICE_PORTA_OLLAMA", 11434),
)
TEMPO_DE_ESPERA_S = 1.5

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

AVISO = (
    "A busca por significado no código está FORA DO AR — {}.\n"
    "Enquanto isso a ferramenta do índice devolve erro, e a alternativa é "
    "`grep`, que custa umas cinco vezes mais contexto por pergunta e não "
    "acha por significado.\n"
    "Para levantar: `docker compose -f .agents/indice/docker-compose.yml "
    "up -d`. Se você não vai usar o índice nesta sessão, ignore — isto é "
    "aviso, não parede."
)
UMA_PECA = "{} não respondeu na porta {}"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def o_modulo_esta_por_perto(raiz: Path) -> bool:
    return any((raiz / onde).is_file() for onde in ONDE_O_MODULO_PODE_ESTAR)


def a_porta_responde(porta: int, tempo=TEMPO_DE_ESPERA_S) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=tempo):
            return True
    except OSError:
        return False


def pecas_fora(ambiente, responde=a_porta_responde) -> list:
    caidas = []
    for rotulo, variavel, padrao in PECAS:
        declarada = str(ambiente.get(variavel) or padrao)
        porta = int(declarada) if declarada.isdigit() else padrao
        if not responde(porta):
            caidas.append(UMA_PECA.format(rotulo, porta))
    return caidas


def decisao(raiz: Path, ambiente, responde=a_porta_responde) -> str:
    if not o_modulo_esta_por_perto(raiz):
        return ""
    caidas = pecas_fora(ambiente, responde)
    return AVISO.format(" e ".join(caidas)) if caidas else ""


def main() -> int:
    try:
        aviso = decisao(raiz_do_projeto_nunca_o_cwd(), os.environ)
    except Exception:
        return SILENCIO
    if aviso:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
            "additionalContext": aviso}}, ensure_ascii=False))
    return SILENCIO


def testar() -> int:
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory(prefix="aviso-indice-") as pasta:
        raiz = Path(pasta)
        tudo_fora = lambda porta: False
        tudo_de_pe = lambda porta: True

        caso("sem o módulo instalado o gancho cala — quem não usa o índice "
             "não é avisado de container que não lhe interessa",
             decisao(raiz, {}, tudo_fora) == "")

        alvo = raiz / ONDE_O_MODULO_PODE_ESTAR[0]
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("services:\n", encoding="utf-8")
        caso("índice declarado e containers de pé: cala",
             decisao(raiz, {}, tudo_de_pe) == "")

        dito = decisao(raiz, {}, tudo_fora)
        caso("índice declarado e containers fora: avisa", bool(dito))
        caso("e nomeia as duas peças com as portas",
             "19530" in dito and "11434" in dito)
        caso("e diz como levantar", "docker compose" in dito)
        caso("e deixa claro que é aviso, não parede",
             "não é parede" in dito or "não parede" in dito
             or "aviso, não parede" in dito)

        so_o_milvus = lambda porta: porta != 19530
        dito = decisao(raiz, {}, so_o_milvus)
        caso("com só uma peça fora, só ela é nomeada",
             "19530" in dito and "11434" not in dito)

        outra = raiz / ONDE_O_MODULO_PODE_ESTAR[1]
        outra.parent.mkdir(parents=True, exist_ok=True)
        outra.write_text("services:\n", encoding="utf-8")
        alvo.unlink()
        caso("a fonte em modulos/ tambem conta: aqui os containers sobem "
             "dela, sem o modulo instalado em .agents/",
             bool(decisao(raiz, {}, tudo_fora)))

        caso("porta declarada por variável substitui a padrão",
             "29530" in decisao(raiz, {"INDICE_PORTA_MILVUS": "29530"},
                                tudo_fora))
        caso("variável com lixo cai na porta padrão, em vez de estourar",
             "19530" in decisao(raiz, {"INDICE_PORTA_MILVUS": "abc"},
                                tudo_fora))

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: o aviso de índice fora — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
