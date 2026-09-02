import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DESCRICAO_DA_CLI = ("mede se a camada instalada atravessa para outra "
                    "ferramenta de agente: o que ela ensina, o que ela "
                    "cerca, e o que ela custa por sessão")

PONTE = ".agents/travessia/ponte.py"
PASTA_DAS_SKILLS_FONTE = ".agents/skills"
PASTA_DOS_GANCHOS = ".claude/hooks"
ARQUIVO_SETTINGS = ".claude/settings.json"
CHAVE_DOS_GANCHOS = "hooks"
INTERPRETADOR = sys.executable
TEMPO_DE_UMA_SONDA_S = 60
SAIDA_QUE_BARRA = 2

FERRAMENTA = "devin"
ONDE_A_OUTRA_LE_GANCHO = ".devin/hooks.v1.json"
BANDEIRA = f"--{FERRAMENTA}"
RAIZ_QUE_A_OUTRA_DA = "DEVIN_PROJECT_DIR"

BARRA = "barra"
PASSA = "passa"
ORIENTA = "orienta"

CONFIGURACAO_MINIMA = {"diretorios_so_codigo": [".agents"]}
ARQUIVO_EXECUTOR = "nucleo/executor.json"

SONDAS = (
    ("regra 15 — escrever na cópia gerada", BARRA, "edit",
     {"file_path": "{raiz}/.claude/skills/verificacao-adversarial/SKILL.md",
      "old_string": "a", "new_string": "b"}),
    ("regra 12 — reescrever branch protegida", BARRA, "exec",
     {"command": "git push --force origin main"}),
    ("regra 12 — apagar branch protegida", BARRA, "exec",
     {"command": "git branch -D main"}),
    ("regra 9 — commitar sem autorização", BARRA, "exec",
     {"command": "git commit -m qualquer"}),
    ("regra 14 — página nascendo em pasta de código", BARRA, "write",
     {"file_path": "{raiz}/.agents/como-fazer.md", "content": "# guia"}),
    ("regra 8 — ler credencial (orienta, não recusa)", ORIENTA, "exec",
     {"command": "cat .env"}),
    ("escrever no alvo legítimo", PASSA, "write",
     {"file_path": "{raiz}/LEIAME.md", "content": "x"}),
    ("ler é livre", PASSA, "read",
     {"file_path": "{raiz}/AGENTS.md"}),
)

LINHA_DA_SONDA = "  {:<3} {:<44} {}"
DEU_CERTO = "ok "
DEU_ERRADO = "NAO"
TITULO_CERCA = f"O QUE A CAMADA CERCA EM {FERRAMENTA.upper()}"
TITULO_ENSINA = f"O QUE A CAMADA ENSINA EM {FERRAMENTA.upper()}"
TITULO_CUSTA = f"O QUE UMA SESSAO DE {FERRAMENTA.upper()} CUSTA"


def perguntar_a_ponte(raiz, ferramenta, entrada):
    pedido = {"hook_event_name": "PreToolUse", "tool_name": ferramenta,
              "tool_input": {c: str(v).format(raiz=raiz)
                             for c, v in entrada.items()}}
    corrida = subprocess.run(
        [INTERPRETADOR, str(Path(raiz) / PONTE)],
        input=json.dumps(pedido), capture_output=True, text=True,
        cwd=raiz, env=dict(os.environ, **{RAIZ_QUE_A_OUTRA_DA: str(raiz)}),
        timeout=TEMPO_DE_UMA_SONDA_S)
    dito = {}
    try:
        dito = json.loads(corrida.stdout or "{}")
    except (json.JSONDecodeError, ValueError):
        pass
    if corrida.returncode == SAIDA_QUE_BARRA:
        return BARRA
    if dito.get("hookSpecificOutput", {}).get("additionalContext"):
        return ORIENTA
    return PASSA


def medir_as_cercas(raiz):
    print(TITULO_CERCA)
    if not (Path(raiz) / PONTE).exists():
        print(f"  a ponte não está instalada em {PONTE}")
        return 1
    falhas = 0
    for nome, esperado, ferramenta, entrada in SONDAS:
        deu = perguntar_a_ponte(raiz, ferramenta, entrada)
        certo = deu == esperado
        falhas += not certo
        print(LINHA_DA_SONDA.format(DEU_CERTO if certo else DEU_ERRADO,
                                    nome, f"esperado {esperado}, deu {deu}"))
    print(f"  {len(SONDAS) - falhas} de {len(SONDAS)} sondas batem")
    return 1 if falhas else 0


def contar_o_que_ensina(raiz):
    print(TITULO_ENSINA)
    skills = sorted(p.parent.name
                    for p in (Path(raiz) / PASTA_DAS_SKILLS_FONTE).glob("*/SKILL.md"))
    print(f"  skills na fonte: {len(skills)}")
    vistas = subprocess.run([FERRAMENTA, "skills", "list"], cwd=raiz,
                            capture_output=True, text=True,
                            timeout=TEMPO_DE_UMA_SONDA_S).stdout
    faltando = [s for s in skills if s not in vistas]
    print(f"  vistas por {FERRAMENTA}: {len(skills) - len(faltando)}")
    if faltando:
        print(f"  NAO chegaram: {', '.join(faltando)}")
    return 1 if faltando else 0


def custo_de_uma_sessao(raiz, pedido):
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "sessao.json"
        subprocess.run([FERRAMENTA, "-p", "--permission-mode", "auto",
                        "--export", str(saida), "--respect-workspace-trust",
                        "false", "--", pedido],
                       cwd=raiz, capture_output=True, text=True, timeout=900)
        if not saida.exists():
            return None
        return json.loads(saida.read_text(encoding="utf-8"))["final_metrics"]


def medir_o_custo(raiz, pedido):
    print(TITULO_CUSTA)
    print(f"  pedido: {pedido}")
    com = custo_de_uma_sessao(raiz, pedido)
    if com is None:
        print("  a sessão não exportou métrica")
        return 1
    with tempfile.TemporaryDirectory() as nu:
        subprocess.run(["git", "init", "-q", "."], cwd=nu, check=False)
        sem = custo_de_uma_sessao(nu, pedido)
    for rotulo, m in (("com a camada", com), ("sem a camada", sem)):
        if m:
            print(f"  {rotulo:<14} entrada {m['total_prompt_tokens']:>7}"
                  f"  saída {m['total_completion_tokens']:>5}"
                  f"  passos {m['total_steps']:>3}")
    if sem:
        print(f"  a camada cobra {com['total_prompt_tokens'] - sem['total_prompt_tokens']}"
              " tokens de entrada por sessão")
    return 0


def preparar(raiz, alvo):
    subprocess.run(["git", "init", "-q", "."], cwd=alvo, check=False)
    subprocess.run([INTERPRETADOR, str(Path(raiz) / "montar.py"), BANDEIRA],
                   cwd=alvo, capture_output=True, check=False)
    (Path(alvo) / ARQUIVO_EXECUTOR).write_text(
        json.dumps(CONFIGURACAO_MINIMA), encoding="utf-8")
    print(f"camada instalada e ponte ligada em {alvo}")


BANDEIRA_DE_TESTE = "--testar"
VEREDITOS = (BARRA, PASSA, ORIENTA)
MOLDE_DA_RAIZ = "{raiz}"
FALHA = "  FALHA {}: {}"
PLACAR = "travessia: {} de {} casos"
SEM_VEREDITO = "veredito {!r} nao existe"
SEM_TRADUCAO = "a ponte nao conhece a ferramenta {!r}"
SEM_CAMINHO = "sonda de caminho sem molde da raiz: {!r}"
SO_BARRA = "nenhuma sonda espera passa — a suite so mediria recusa"
SO_PASSA = "nenhuma sonda espera barra — a suite nao mediria cerca nenhuma"
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")


def _o_que_a_ponte_traduz():
    fonte = (Path(__file__).parent / "ponte.py").read_text(encoding="utf-8")
    dentro = fonte.split("COMO_A_OUTRA_FERRAMENTA_CHAMA_A_MESMA_COISA = {")[1]
    return {l.split('"')[1] for l in dentro.split("}")[0].splitlines()
            if '"' in l}


def testar():
    quebrou = []
    traduzidas = _o_que_a_ponte_traduz()
    for nome, esperado, ferramenta, entrada in SONDAS:
        if esperado not in VEREDITOS:
            quebrou.append((nome, SEM_VEREDITO.format(esperado)))
        if ferramenta not in traduzidas:
            quebrou.append((nome, SEM_TRADUCAO.format(ferramenta)))
        for campo, valor in entrada.items():
            if campo in CAMPOS_DE_CAMINHO and MOLDE_DA_RAIZ not in str(valor):
                quebrou.append((nome, SEM_CAMINHO.format(valor)))
    esperados = {e for _, e, _, _ in SONDAS}
    if PASSA not in esperados:
        quebrou.append(("a suite inteira", SO_BARRA))
    if BARRA not in esperados:
        quebrou.append(("a suite inteira", SO_PASSA))
    for nome, porque in quebrou:
        print(FALHA.format(nome, porque))
    total = len(SONDAS) + 2
    print(PLACAR.format(total - len(quebrou), total))
    return 1 if quebrou else 0



def main(argv=None):
    p = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    p.add_argument("--raiz", default=".", help="raiz da camada")
    p.add_argument("--em", help="repositório já instalado onde medir")
    p.add_argument("--cerca", action="store_true",
                   help="as cercas atravessam? não abre sessão")
    p.add_argument("--ensina", action="store_true",
                   help="as skills chegam? não abre sessão")
    p.add_argument("--custa", metavar="PEDIDO",
                   help="quanto uma sessão consome; ABRE SESSÃO e paga")
    p.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                   help="prova a própria suíte de sondas")
    a = p.parse_args(argv)
    if a.testar:
        return testar()
    raiz = Path(a.raiz).resolve()

    if a.em:
        return travessia_em(raiz, Path(a.em).resolve(), a)
    with tempfile.TemporaryDirectory() as alvo:
        preparar(raiz, alvo)
        return travessia_em(raiz, Path(alvo), a)


def travessia_em(raiz, alvo, a):
    faltou = 0
    if a.ensina or not (a.cerca or a.custa):
        faltou |= contar_o_que_ensina(alvo)
    if a.cerca or not (a.ensina or a.custa):
        faltou |= medir_as_cercas(alvo)
    if a.custa:
        faltou |= medir_o_custo(alvo, a.custa)
    return faltou


if __name__ == "__main__":
    sys.exit(main())
