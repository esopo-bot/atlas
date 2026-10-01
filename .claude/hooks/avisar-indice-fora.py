import json
import os
import shutil
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
ONDE_O_MODULO_PODE_ESTAR = (
    ".agents/indice/buscar.py",
    "modulos/indice/.agents/indice/buscar.py",
)
PROGRAMA_DO_INDICE = "ck"

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

AVISO = (
    "O `ck` não está no PATH — a busca do acervo "
    "(`python .agents/indice/buscar.py`) cai no grep, por palavra e sem "
    "ranking, e a ronda do índice não indexa.\n"
    "A receita de instalar está em conhecimento/indice.md. Se você não vai "
    "usar o índice nesta sessão, ignore — isto é aviso, não parede."
)


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def o_modulo_esta_por_perto(raiz: Path) -> bool:
    return any((raiz / onde).is_file() for onde in ONDE_O_MODULO_PODE_ESTAR)


def o_programa_no_path() -> str:
    return shutil.which(PROGRAMA_DO_INDICE) or ""


def decisao(raiz: Path, localizar=o_programa_no_path) -> str:
    if not o_modulo_esta_por_perto(raiz):
        return ""
    return "" if localizar() else AVISO


def main() -> int:
    try:
        aviso = decisao(raiz_do_projeto_nunca_o_cwd())
    except Exception:
        return SILENCIO
    if aviso:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
            "additionalContext": aviso}}))
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
        sem_ck = lambda: ""
        com_ck = lambda: "/bin/ck"

        caso("sem o módulo instalado o gancho cala — quem não usa o índice "
             "não é avisado de programa que não lhe interessa",
             decisao(raiz, sem_ck) == "")

        alvo = raiz / ONDE_O_MODULO_PODE_ESTAR[0]
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("", encoding="utf-8")
        caso("módulo instalado e o ck no PATH: cala, sem sondar serviço",
             decisao(raiz, com_ck) == "")

        dito = decisao(raiz, sem_ck)
        caso("módulo instalado e sem o ck: avisa e nomeia o ck",
             "`ck`" in dito and "PATH" in dito)
        caso("e diz que a busca cai no grep, e onde está a receita",
             "grep" in dito and "conhecimento/indice.md" in dito)
        caso("e deixa claro que é aviso, não parede",
             "aviso, não parede" in dito)
        caso("e não fala mais de banco, porta nem contêiner",
             "porta" not in dito and "docker" not in dito)

        outra = raiz / ONDE_O_MODULO_PODE_ESTAR[1]
        outra.parent.mkdir(parents=True, exist_ok=True)
        outra.write_text("", encoding="utf-8")
        alvo.unlink()
        caso("a fonte em modulos/ também conta: aqui o módulo mora nela, sem "
             "a cópia instalada em .agents/",
             bool(decisao(raiz, sem_ck)))

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: o aviso do ck ausente — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
