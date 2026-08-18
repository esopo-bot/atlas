#!/usr/bin/env python3
"""limpeza — gera e roda a rotina que arruma o workspace antes do trabalho.

O PORQUÊ: quem dispara o executor de roteiros num workspace grande paga por
sujeira que ninguém vê — artefato de build que o disco carrega, branch base
atrasada em relação ao remoto, e trabalho que ficou sem entrar na
integração. Nada disso é defeito de código; é o chão sujo antes de começar.

DUAS PEÇAS, e a divisão importa:

- **Este arquivo VIAJA** com a camada: é o mecanismo, e não sabe nada de
  ninguém.
- **A rotina GERADA é local** e não entra em git. Ela nasce do inventário
  medido no dia — cada repositório com a linguagem e a branch padrão dele —
  e mora no caminho que `arquivo_limpeza` declara em `nucleo/executor.json`.

A REGRA DURA DA REMOÇÃO: por padrão ela só RELATA. Só com `--aplicar` remove,
e só o que um comando de build recria sozinho. **Nunca** toca arquivo
rastreado pelo git, `.env`, configuração local, worktree — nem
`node_modules`, que é regenerável mas caro de repor, e por isso ficou de fora
por decisão. Destrutivo é do dono (regra 9): o automático se limita ao que
não custa nada refazer.

Uso:
    limpeza.py inventariar --workspace D          # o que existe, medido
    limpeza.py gerar --workspace D --destino F    # escreve a rotina local
    limpeza.py rodar --workspace D [--aplicar]    # relata; com --aplicar, remove

Rode os testes com:  python .agents/limpeza/limpeza.py --testar
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# O que um build recria sozinho. `node_modules` NÃO está aqui de propósito:
# regenerável, sim; barato de repor, não — e a decisão do dono foi deixá-lo
# de fora até que alguém peça uma bandeira própria para ele.
REGENERAVEL = ("bin", "obj", "dist", "build", "out", "__pycache__",
               ".pytest_cache", ".mypy_cache", "target")
# Marcador → linguagem. Serve para a rotina saber o que esperar de cada
# repositório, e para o relatório dizer o que está olhando.
MARCADORES = (("package.json", "node"), ("pyproject.toml", "python"),
              ("requirements.txt", "python"), ("go.mod", "go"),
              ("Cargo.toml", "rust"), ("pom.xml", "java"),
              ("build.gradle", "java"), ("*.csproj", "dotnet"),
              ("*.sln", "dotnet"))


def _git(repo, *args, tempo=30):
    try:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=tempo)
    except (OSError, subprocess.SubprocessError):
        return None


def linguagem_de(repo: Path) -> str:
    for padrao, nome in MARCADORES:
        achou = list(repo.glob(padrao)) if "*" in padrao \
            else ([repo / padrao] if (repo / padrao).exists() else [])
        if achou:
            return nome
    return "desconhecida"


def branch_padrao_de(repo: Path) -> str:
    """A branch padrão do remoto; sem remoto, a que está em curso."""
    achado = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if achado and achado.returncode == 0 and achado.stdout.strip():
        return achado.stdout.strip().split("/")[-1]
    achado = _git(repo, "branch", "--show-current")
    return achado.stdout.strip() if achado and achado.stdout.strip() else "main"


def inventariar(workspace: Path) -> list:
    """Um item por repositório do workspace, medido agora."""
    repositorios = []
    for caminho in sorted(p.parent for p in workspace.glob("*/.git")):
        repositorios.append({
            "caminho": str(caminho),
            "nome": caminho.name,
            "linguagem": linguagem_de(caminho),
            "branch_padrao": branch_padrao_de(caminho),
        })
    return repositorios


def _artefatos(repo: Path) -> list:
    """As pastas regeneráveis deste repositório — e só as NÃO rastreadas.

    O cheque contra o git é a trava que importa: pasta chamada `bin/` que
    alguém commitou de propósito é código de outra pessoa, não artefato.
    """
    achados = []
    for nome in REGENERAVEL:
        for pasta in repo.rglob(nome):
            if not pasta.is_dir() or ".git" in pasta.parts:
                continue
            relativo = pasta.relative_to(repo)
            rastreado = _git(repo, "ls-files", "--error-unmatch",
                             str(relativo))
            if rastreado and rastreado.returncode == 0:
                continue  # rastreado: é de alguém, não é artefato
            achados.append(pasta)
    return achados


def olhar(repo: dict, integracao=None) -> dict:
    """O relatório de um repositório: artefatos, base atrasada, não mesclado."""
    caminho = Path(repo["caminho"])
    achado = {"nome": repo["nome"], "linguagem": repo["linguagem"],
              "artefatos": [str(p) for p in _artefatos(caminho)],
              "base_atrasada": None, "nao_mesclado": []}

    base = repo["branch_padrao"]
    atras = _git(caminho, "rev-list", "--count", f"{base}..origin/{base}")
    if atras and atras.returncode == 0 and atras.stdout.strip().isdigit():
        quantos = int(atras.stdout.strip())
        achado["base_atrasada"] = quantos if quantos else None

    alvo = integracao or base
    nao = _git(caminho, "branch", "--no-merged", alvo, "--format=%(refname:short)")
    if nao and nao.returncode == 0:
        achado["nao_mesclado"] = [b for b in nao.stdout.split() if b != alvo]
    return achado


def relatar(repositorios: list, integracao=None, aplicar=False) -> int:
    """Imprime o relatório. Com aplicar=True, remove o regenerável."""
    removidos = 0
    for repo in repositorios:
        visto = olhar(repo, integracao)
        print(f"\n{visto['nome']} ({visto['linguagem']})")
        if visto["artefatos"]:
            print(f"  artefato regenerável: {len(visto['artefatos'])} pasta(s)")
            for pasta in visto["artefatos"][:5]:
                print(f"    {pasta}")
            if aplicar:
                import shutil
                for pasta in visto["artefatos"]:
                    shutil.rmtree(pasta, ignore_errors=True)
                    removidos += 1
                print(f"  removidas {len(visto['artefatos'])} pasta(s)")
        if visto["base_atrasada"]:
            print(f"  base {visto['base_atrasada']} commit(s) atrás do remoto")
        if visto["nao_mesclado"]:
            print("  não mesclado na integração: "
                  + ", ".join(visto["nao_mesclado"][:5]))
        if not any((visto["artefatos"], visto["base_atrasada"],
                    visto["nao_mesclado"])):
            print("  em dia")
    print(f"\n{len(repositorios)} repositórios"
          + (f", {removidos} pastas removidas" if aplicar
             else " — nada removido (use --aplicar)"))
    return 0


MOLDE = '''#!/usr/bin/env python3
"""A rotina de limpeza DESTE workspace — gerada em {quando}.

Arquivo LOCAL: não entra em git. O mecanismo viaja na camada
(.agents/limpeza/limpeza.py); o que mora aqui é o inventário medido no dia.
Regerar quando repositório entrar ou sair:
    python .agents/limpeza/limpeza.py gerar --workspace {workspace} --destino {destino}

Por padrão RELATA. Só com --aplicar remove, e só o regenerável.
"""
import subprocess
import sys

WORKSPACE = {workspace!r}
MECANISMO = {mecanismo!r}
REPOSITORIOS = {repositorios}

if __name__ == "__main__":
    sys.exit(subprocess.run(
        [sys.executable, MECANISMO, "rodar", "--workspace", WORKSPACE]
        + sys.argv[1:]).returncode)
'''


def gerar(workspace: Path, destino: Path) -> int:
    from datetime import datetime
    repositorios = inventariar(workspace)
    if not repositorios:
        print(f"erro de uso: nenhum repositório git em {workspace}",
              file=sys.stderr)
        return 2
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(MOLDE.format(
        quando=datetime.now().astimezone().isoformat(timespec="seconds"),
        workspace=str(workspace), destino=str(destino),
        mecanismo=str(Path(__file__).resolve()),
        repositorios=json.dumps(repositorios, ensure_ascii=False, indent=4),
    ), encoding="utf-8")
    print(f"rotina escrita em {destino} — {len(repositorios)} repositórios "
          f"({', '.join(r['nome'] for r in repositorios[:5])})")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser(prog="limpeza.py")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome in ("inventariar", "gerar", "rodar"):
        p = sub.add_parser(nome)
        p.add_argument("--workspace", required=True)
        if nome == "gerar":
            p.add_argument("--destino", required=True)
        if nome == "rodar":
            p.add_argument("--aplicar", action="store_true",
                           help="remove o artefato regenerável (o padrão é "
                                "só relatar)")
            p.add_argument("--integracao",
                           help="a branch de integração, para acusar o que "
                                "não entrou nela")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"erro de uso: --workspace {workspace} não existe",
              file=sys.stderr)
        return 2
    if args.comando == "inventariar":
        print(json.dumps(inventariar(workspace), ensure_ascii=False, indent=2))
        return 0
    if args.comando == "gerar":
        return gerar(workspace, Path(args.destino))
    return relatar(inventariar(workspace), args.integracao, args.aplicar)


# --- Testes -----------------------------------------------------------------

def _repo_de_mentira(raiz: Path, nome, linguagem, sujeira, branch_extra=None):
    repo = raiz / nome
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(repo)], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"],
                   capture_output=True)
    marcador = {"node": "package.json", "python": "pyproject.toml",
                "dotnet": "app.csproj"}[linguagem]
    (repo / marcador).write_text("{}", encoding="utf-8")
    for pasta in sujeira:
        (repo / pasta).mkdir(parents=True, exist_ok=True)
        (repo / pasta / "artefato.bin").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", marcador],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"],
                   capture_output=True)
    if branch_extra:
        subprocess.run(["git", "-C", str(repo), "checkout", "-qb", branch_extra],
                       capture_output=True)
        (repo / "novo.txt").write_text("a", encoding="utf-8")
        # `add -A` aqui rastrearia a sujeira, e voltar para a base a
        # apagaria do disco — o fixture mentiria sobre o que existe.
        subprocess.run(["git", "-C", str(repo), "add", "novo.txt"],
                       capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "trabalho"],
                       capture_output=True)
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-"],
                       capture_output=True)
    return repo


def testar() -> int:
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    with tempfile.TemporaryDirectory(prefix="limpeza-teste-") as tmp:
        raiz = Path(tmp)
        node = _repo_de_mentira(raiz, "app-node", "node",
                                ["dist", "node_modules"], "trabalho/x")
        _repo_de_mentira(raiz, "app-dotnet", "dotnet", ["bin", "obj"])
        (raiz / "nao-e-repo").mkdir()

        inventario = inventariar(raiz)
        caso("o inventário acha só os repositórios git",
             [r["nome"] for r in inventario] == ["app-dotnet", "app-node"])
        caso("e identifica a linguagem de cada um",
             {r["nome"]: r["linguagem"] for r in inventario}
             == {"app-node": "node", "app-dotnet": "dotnet"})

        visto = olhar([r for r in inventario if r["nome"] == "app-node"][0])
        nomes = {Path(p).name for p in visto["artefatos"]}
        caso("acha o artefato regenerável", "dist" in nomes)
        caso("e NÃO toca node_modules (decisão do dono)",
             "node_modules" not in nomes)
        caso("acusa trabalho não mesclado",
             "trabalho/x" in visto["nao_mesclado"])

        # a trava: pasta regenerável que alguém RASTREOU não é artefato
        rastreada = node / "build"
        rastreada.mkdir()
        (rastreada / "importante.txt").write_text("meu", encoding="utf-8")
        subprocess.run(["git", "-C", str(node), "add", "-f", "build"],
                       capture_output=True)
        subprocess.run(["git", "-C", str(node), "commit", "-qm", "build"],
                       capture_output=True)
        visto = olhar([r for r in inventario if r["nome"] == "app-node"][0])
        caso("pasta regenerável RASTREADA não é tocada",
             "build" not in {Path(p).name for p in visto["artefatos"]})

        # relatar não remove; --aplicar remove
        dist = node / "dist"
        relatar(inventario)
        caso("o padrão não remove nada", dist.is_dir())
        relatar(inventario, aplicar=True)
        caso("com --aplicar o regenerável some", not dist.is_dir())
        caso("e o rastreado continua lá", rastreada.is_dir())
        caso("e node_modules continua lá", (node / "node_modules").is_dir())

        destino = raiz / "rotina-local.py"
        caso("gerar escreve a rotina local", gerar(raiz, destino) == 0
             and destino.is_file())
        caso("a rotina gerada carrega o inventário medido",
             "app-node" in destino.read_text(encoding="utf-8"))
        caso("workspace sem repositório nenhum é erro de uso",
             gerar(raiz / "nao-e-repo", raiz / "x.py") == 2)

    falhas = [r for r, ok in resultados if not ok]
    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {len(resultados)} casos")
        return 1
    print(f"OK: {len(resultados)} casos")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(f"erro de ambiente: {ambiente}", file=sys.stderr)
        sys.exit(2)
