"""Gancho PreToolUse: nega apagar, renomear e forçar branch de longa duração.

Regra 12 da camada. Regra de texto erra dos dois lados — `git push origin
+feature/x` é push forçado e `git push origin feature/x` não é, e nenhum
padrão separa os dois. Este gancho lê o comando e separa.

Ele nega só o destrutivo sobre branch protegida: apagar, renomear e reescrever.
Push normal, commit, checkout e branch nova passam sem saber que ele existe.

Os nomes vêm de `.claude/branches-protegidas.txt` (um por linha). Sem o
arquivo, vale a lista embutida — o gancho nunca fica sem lista.

Rode os testes com:  python .claude/hooks/vetar-branch-protegida.py --testar
"""

import json
import re
import subprocess
import sys
from pathlib import Path

PADRAO = {
    "main", "master", "trunk",
    "develop", "development",
    "homolog", "homologacao", "staging", "stage", "hml", "qa", "uat",
    "release", "prod", "producao", "production",
}

# Bandeiras globais do git que vêm ANTES do verbo. As da segunda lista comem o
# token seguinte — sem isso, `git -C /tmp push` faz o verbo virar "/tmp".
GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare", "--literal-pathspecs"}
GLOBAIS_COM_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

SEPARADORES = re.compile(r"&&|\|\||;|\|")


def nomes_protegidos(raiz: Path) -> set:
    arquivo = raiz / ".claude/branches-protegidas.txt"
    try:
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set(PADRAO)
    nomes = {l.strip().lower() for l in linhas
             if l.strip() and not l.strip().startswith("#")}
    return nomes or set(PADRAO)


def alvo_do_ref(ref: str) -> str:
    """De um refspec para o nome da branch de DESTINO, em minúsculas.

    `+origem:destino` empurra em destino; `:destino` apaga destino; `nome`
    empurra em nome. É sempre o lado direito que sofre.
    """
    ref = ref.strip().lstrip("+")
    if ":" in ref:
        ref = ref.split(":", 1)[1]
    ref = re.sub(r"^refs/heads/", "", ref)
    return ref.strip().lower()


def e_git(token: str) -> bool:
    """O nome do programa é o basename, em minúsculas.

    Comparar o token inteiro com "git" deixa passar `git.exe`, `/usr/bin/git`
    e o caminho absoluto com espaço no meio.
    """
    return Path(token.replace("\\", "/")).name.lower() in {"git", "git.exe"}


def partir(segmento: str) -> list:
    try:
        import shlex
        return shlex.split(segmento, posix=False)
    except ValueError:
        return segmento.split()


def verbo_e_resto(tokens: list):
    """Pula as bandeiras globais e devolve (verbo, argumentos depois dele)."""
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in GLOBAIS_COM_VALOR:
            i += 2
            continue
        if any(t.startswith(g + "=") for g in GLOBAIS_COM_VALOR) or t in GLOBAIS_SIMPLES:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        return t.lower(), tokens[i + 1:]
    return None, []


def branch_atual(raiz: Path):
    """Só é consultada quando o comando força sem dizer qual ref."""
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           cwd=raiz, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    nome = r.stdout.strip().lower()
    return nome if r.returncode == 0 and nome and nome != "head" else None


def motivo_da_recusa(comando: str, protegidas: set, raiz: Path):
    """Devolve o motivo se o comando é destrutivo sobre branch protegida."""
    for segmento in SEPARADORES.split(comando):
        tokens = partir(segmento.strip())
        if not tokens or not e_git(tokens[0]):
            continue
        verbo, resto = verbo_e_resto(tokens)
        if verbo not in {"push", "branch"}:
            continue

        bandeiras = {t.lower() for t in resto if t.startswith("-")}
        refs = [alvo_do_ref(t) for t in resto if not t.startswith("-")]
        atingidas = [r for r in refs if r in protegidas]

        if verbo == "branch":
            apaga = bandeiras & {"-d", "-D".lower(), "--delete"} or "-D" in resto
            renomeia = bandeiras & {"-m", "-M".lower(), "--move"} or "-M" in resto
            if (apaga or renomeia) and atingidas:
                acao = "apagar" if apaga else "renomear"
                return f"{acao} a branch protegida '{atingidas[0]}'"
            continue

        # push
        apaga = bool(bandeiras & {"-d", "--delete"})
        forca = bool(bandeiras & {"-f", "--force"}) or any(
            b.startswith("--force-with-lease") or b.startswith("--force-if-includes")
            for b in bandeiras)
        apaga_por_refspec = [alvo_do_ref(t) for t in resto
                             if not t.startswith("-") and t.startswith(":")]
        forca_por_refspec = [alvo_do_ref(t) for t in resto
                             if not t.startswith("-") and t.startswith("+")]

        for nome in apaga_por_refspec:
            if nome in protegidas:
                return f"apagar a branch protegida '{nome}' (refspec com dois-pontos)"
        for nome in forca_por_refspec:
            if nome in protegidas:
                return f"reescrever a branch protegida '{nome}' (refspec com mais)"
        if apaga and atingidas:
            return f"apagar a branch protegida '{atingidas[0]}'"
        if forca and atingidas:
            return f"reescrever a história da branch protegida '{atingidas[0]}'"
        if forca and not refs:
            atual = branch_atual(raiz)
            if atual in protegidas:
                return f"reescrever a história de '{atual}', a branch atual e protegida"
    return None


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return 0  # falha aberto: entrada quebrada não prende a sessão

    if not comando or "git" not in comando.lower():
        return 0

    raiz = Path.cwd()
    motivo = motivo_da_recusa(comando, nomes_protegidos(raiz), raiz)
    if not motivo:
        return 0  # passagem é silêncio: sair 0 sem imprimir nada

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"Regra 12 da camada: isto quer {motivo}. Branch de longa duração "
            "é infraestrutura de outras pessoas — desfazer é público e caro. "
            "O caminho: trabalhe na sua branch e peça a promoção ao dono, que "
            "roda o comando ele mesmo. Se esta branch não deveria estar "
            "protegida, tire o nome de .claude/branches-protegidas.txt."
        ),
    }}))
    return 0


# --- Testes -----------------------------------------------------------------
# Duas listas, e a segunda é a que importa: veto largo demais é desligado na
# primeira semana. Metade dos casos existe para provar que ele NÃO atrapalha.

BARRA = [
    ("apagar local, forma óbvia", "git branch -d homolog"),
    ("apagar local, maiúscula", "git branch -D develop"),
    ("apagar no remoto", "git push origin --delete homolog"),
    ("apagar por refspec", "git push origin :homolog"),
    ("forçar, forma óbvia", "git push --force origin main"),
    ("forçar, o que o glob não pega", "git push origin +homolog"),
    ("forçar com lease ainda reescreve", "git push --force-with-lease origin develop"),
    ("escondida depois de &&", "git status && git push --force origin homolog"),
    ("bandeira antes do verbo", "git -C /tmp/x push --force origin main"),
    ("configuração antes do verbo", "git -c user.name=x branch -D main"),
    ("caminho absoluto do programa", "/usr/bin/git branch -d homolog"),
    ("no Windows, com .exe", "git.exe push origin --delete main"),
    ("renomear a protegida", "git branch -m develop develop-velha"),
    ("refs/heads explícito", "git push origin +refs/heads/main"),
    ("forçar na forma curta", "git push -f origin homolog"),
    ("caminho do Windows antes do verbo", r"git -C C:\repo push --force origin main"),
]

DEIXA_PASSAR = [
    ("push normal na protegida", "git push origin develop"),
    ("push normal, sem ref", "git push"),
    ("apagar branch de trabalho", "git branch -d feature/x"),
    ("forçar branch de trabalho", "git push --force origin feature/x"),
    ("nome que só parece", "git branch -d develop-antiga"),
    ("nome que contém a protegida", "git push origin --delete feature/main-menu"),
    ("outro programa", "docker push imagem:main"),
    ("commit comum", "git commit -m 'apaga develop do texto'"),
    ("criar branch a partir da protegida", "git branch feature/nova develop"),
    ("checkout da protegida", "git checkout main"),
    ("buscar do remoto", "git fetch origin main"),
    ("listar branches", "git branch -a"),
    # O limite declarado: push normal para branch protegida PASSA aqui. Quem
    # decide isso é a regra 9 e o perfil do repositório — este gancho cuida do
    # destrutivo. Veto largo demais é desligado na primeira semana.
    ("push normal para a protegida", "git push origin main"),
]


def testar() -> int:
    protegidas = set(PADRAO)
    raiz = Path.cwd()
    falhas = []
    for rotulo, comando in BARRA:
        if not motivo_da_recusa(comando, protegidas, raiz):
            falhas.append(f"  DEVIA BARRAR e passou — {rotulo}: {comando}")
    for rotulo, comando in DEIXA_PASSAR:
        motivo = motivo_da_recusa(comando, protegidas, raiz)
        if motivo:
            falhas.append(f"  DEVIA PASSAR e barrou — {rotulo}: {comando} ({motivo})")
    total = len(BARRA) + len(DEIXA_PASSAR)
    if falhas:
        print(f"FALHOU: {len(falhas)} de {total} casos")
        print("\n".join(falhas))
        return 1
    print(f"OK: {total} casos — {len(BARRA)} barrados, {len(DEIXA_PASSAR)} liberados")
    return 0


if __name__ == "__main__":
    sys.exit(testar() if "--testar" in sys.argv else main())
