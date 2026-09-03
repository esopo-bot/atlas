
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REGENERAVEL_BARATO_DE_REFAZER = ("bin", "obj", "dist", "build", "out",
                                 "__pycache__", ".pytest_cache",
                                 ".mypy_cache", "target")
MARCADOR_DA_LINGUAGEM = (("package.json", "node"), ("pyproject.toml", "python"),
                         ("requirements.txt", "python"), ("go.mod", "go"),
                         ("Cargo.toml", "rust"), ("pom.xml", "java"),
                         ("build.gradle", "java"), ("*.csproj", "dotnet"),
                         ("*.sln", "dotnet"))
LINGUAGEM_DESCONHECIDA = "desconhecida"
BRANCH_PADRAO_SEM_REMOTO = "main"
TEMPO_LIMITE_DO_GIT = 30
QUANTOS_EXEMPLOS_MOSTRAR = 5
COMANDOS = ("inventariar", "gerar", "rodar")

RELATO_CABECALHO = "\n{} ({})"
RELATO_ARTEFATOS = "  artefato regenerável: {} pasta(s)"
RELATO_PASTA = "    {}"
RELATO_REMOVIDAS = "  removidas {} pasta(s)"
RELATO_BASE_ATRASADA = "  base {} commit(s) atrás do remoto"
RELATO_NAO_MESCLADO = "  não mesclado na integração: {}"
RELATO_EM_DIA = "  em dia"
RELATO_RODAPE = "\n{} repositórios"
RELATO_RODAPE_REMOVIDAS = ", {} pastas removidas"
RELATO_RODAPE_NADA_REMOVIDO = " — nada removido (use --aplicar)"
RELATO_ROTINA_ESCRITA = "rotina escrita em {} — {} repositórios ({})"

ERRO_SEM_REPOSITORIO = "erro de uso: nenhum repositório git em {}"
ERRO_WORKSPACE_INEXISTENTE = "erro de uso: --workspace {} não existe"
ERRO_DE_AMBIENTE = "erro de ambiente: {}"

AJUDA_APLICAR = "remove o artefato regenerável (o padrão é só relatar)"
AJUDA_INTEGRACAO = "a branch de integração, para acusar o que não entrou nela"

TESTE_FALHA = "FALHOU: {}"
TESTE_RESUMO_FALHA = "FALHOU: {} de {} casos"
TESTE_RESUMO_OK = "OK: {} casos"

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


def _git(repo, *args, tempo_limite=TEMPO_LIMITE_DO_GIT):
    try:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=tempo_limite)
    except (OSError, subprocess.SubprocessError):
        return None


def linguagem_de(repo: Path) -> str:
    for padrao, nome in MARCADOR_DA_LINGUAGEM:
        achou = list(repo.glob(padrao)) if "*" in padrao \
            else ([repo / padrao] if (repo / padrao).exists() else [])
        if achou:
            return nome
    return LINGUAGEM_DESCONHECIDA


def branch_padrao_de(repo: Path) -> str:
    do_remoto = _git(repo, "symbolic-ref", "--short",
                     "refs/remotes/origin/HEAD")
    if do_remoto and do_remoto.returncode == 0 and do_remoto.stdout.strip():
        return do_remoto.stdout.strip().split("/")[-1]
    em_curso = _git(repo, "branch", "--show-current")
    if em_curso and em_curso.stdout.strip():
        return em_curso.stdout.strip()
    return BRANCH_PADRAO_SEM_REMOTO


def inventariar(workspace: Path) -> list:
    repositorios = []
    for caminho in sorted(p.parent for p in workspace.glob("*/.git")):
        repositorios.append({
            "caminho": str(caminho),
            "nome": caminho.name,
            "linguagem": linguagem_de(caminho),
            "branch_padrao": branch_padrao_de(caminho),
        })
    return repositorios


def _rastreada_pelo_git(repo: Path, pasta: Path) -> bool:
    resposta = _git(repo, "ls-files", "--error-unmatch",
                    str(pasta.relative_to(repo)))
    return bool(resposta and resposta.returncode == 0)


def artefatos_nao_rastreados(repo: Path) -> list:
    achados = []
    for nome in REGENERAVEL_BARATO_DE_REFAZER:
        for pasta in repo.rglob(nome):
            if not pasta.is_dir() or ".git" in pasta.parts:
                continue
            if _rastreada_pelo_git(repo, pasta):
                continue
            achados.append(pasta)
    return achados


def _quantos_commits_atras_do_remoto(repo: Path, base: str):
    atras = _git(repo, "rev-list", "--count", f"{base}..origin/{base}")
    if atras and atras.returncode == 0 and atras.stdout.strip().isdigit():
        return int(atras.stdout.strip()) or None
    return None


def _branches_nao_mescladas(repo: Path, alvo: str) -> list:
    nao = _git(repo, "branch", "--no-merged", alvo,
               "--format=%(refname:short)")
    if nao and nao.returncode == 0:
        return [b for b in nao.stdout.split() if b != alvo]
    return []


def relatorio_do_repositorio(repo: dict, integracao=None) -> dict:
    caminho = Path(repo["caminho"])
    base = repo["branch_padrao"]
    return {
        "nome": repo["nome"],
        "linguagem": repo["linguagem"],
        "artefatos": [str(p) for p in artefatos_nao_rastreados(caminho)],
        "base_atrasada": _quantos_commits_atras_do_remoto(caminho, base),
        "nao_mesclado": _branches_nao_mescladas(caminho, integracao or base),
    }


def _remover(pastas: list) -> int:
    import shutil
    for pasta in pastas:
        shutil.rmtree(pasta, ignore_errors=True)
    return len(pastas)


def _imprimir_relatorio(visto: dict, aplicar: bool) -> int:
    print(RELATO_CABECALHO.format(visto["nome"], visto["linguagem"]))
    removidos = 0
    if visto["artefatos"]:
        print(RELATO_ARTEFATOS.format(len(visto["artefatos"])))
        for pasta in visto["artefatos"][:QUANTOS_EXEMPLOS_MOSTRAR]:
            print(RELATO_PASTA.format(pasta))
        if aplicar:
            removidos = _remover(visto["artefatos"])
            print(RELATO_REMOVIDAS.format(removidos))
    if visto["base_atrasada"]:
        print(RELATO_BASE_ATRASADA.format(visto["base_atrasada"]))
    if visto["nao_mesclado"]:
        print(RELATO_NAO_MESCLADO.format(
            ", ".join(visto["nao_mesclado"][:QUANTOS_EXEMPLOS_MOSTRAR])))
    if not any((visto["artefatos"], visto["base_atrasada"],
                visto["nao_mesclado"])):
        print(RELATO_EM_DIA)
    return removidos


def relatar(repositorios: list, integracao=None, aplicar=False) -> int:
    removidos = 0
    for repo in repositorios:
        removidos += _imprimir_relatorio(
            relatorio_do_repositorio(repo, integracao), aplicar)
    print(RELATO_RODAPE.format(len(repositorios))
          + (RELATO_RODAPE_REMOVIDAS.format(removidos) if aplicar
             else RELATO_RODAPE_NADA_REMOVIDO))
    return 0


def gerar(workspace: Path, destino: Path) -> int:
    from datetime import datetime
    repositorios = inventariar(workspace)
    if not repositorios:
        print(ERRO_SEM_REPOSITORIO.format(workspace), file=sys.stderr)
        return 2
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(MOLDE.format(
        quando=datetime.now().astimezone().isoformat(timespec="seconds"),
        workspace=str(workspace), destino=str(destino),
        mecanismo=str(Path(__file__).resolve()),
        repositorios=json.dumps(repositorios, ensure_ascii=False, indent=4),
    ), encoding="utf-8")
    exemplos = ", ".join(r["nome"]
                         for r in repositorios[:QUANTOS_EXEMPLOS_MOSTRAR])
    print(RELATO_ROTINA_ESCRITA.format(destino, len(repositorios), exemplos))
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="limpeza.py")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome in COMANDOS:
        p = sub.add_parser(nome)
        p.add_argument("--workspace", required=True)
        if nome == "gerar":
            p.add_argument("--destino", required=True)
        if nome == "rodar":
            p.add_argument("--aplicar", action="store_true",
                           help=AJUDA_APLICAR)
            p.add_argument("--integracao", help=AJUDA_INTEGRACAO)
    return parser


def main(argv) -> int:
    args = montar_parser().parse_args(argv)
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(ERRO_WORKSPACE_INEXISTENTE.format(workspace), file=sys.stderr)
        return 2
    if args.comando == "inventariar":
        print(json.dumps(inventariar(workspace), ensure_ascii=False, indent=2))
        return 0
    if args.comando == "gerar":
        return gerar(workspace, Path(args.destino))
    return relatar(inventariar(workspace), args.integracao, args.aplicar)


def _commitar_so_este_arquivo(repo: Path, arquivo: str, mensagem: str):
    subprocess.run(["git", "-C", str(repo), "add", arquivo],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", mensagem],
                   capture_output=True)


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
    _commitar_so_este_arquivo(repo, marcador, "base")
    if branch_extra:
        subprocess.run(["git", "-C", str(repo), "checkout", "-qb",
                        branch_extra], capture_output=True)
        (repo / "novo.txt").write_text("a", encoding="utf-8")
        _commitar_so_este_arquivo(repo, "novo.txt", "trabalho")
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-"],
                       capture_output=True)
    return repo


def _rastrear_de_proposito(repo: Path, nome: str) -> Path:
    pasta = repo / nome
    pasta.mkdir()
    (pasta / "importante.txt").write_text("meu", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-f", nome],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", nome],
                   capture_output=True)
    return pasta


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

        do_node = [r for r in inventario if r["nome"] == "app-node"][0]
        visto = relatorio_do_repositorio(do_node)
        nomes = {Path(p).name for p in visto["artefatos"]}
        caso("acha o artefato regenerável", "dist" in nomes)
        caso("e NÃO toca node_modules (decisão do dono)",
             "node_modules" not in nomes)
        caso("acusa trabalho não mesclado",
             "trabalho/x" in visto["nao_mesclado"])

        rastreada = _rastrear_de_proposito(node, "build")
        visto = relatorio_do_repositorio(do_node)
        caso("pasta regenerável RASTREADA não é tocada",
             "build" not in {Path(p).name for p in visto["artefatos"]})

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
            print(TESTE_FALHA.format(falha))
        print(TESTE_RESUMO_FALHA.format(len(falhas), len(resultados)))
        return 1
    print(TESTE_RESUMO_OK.format(len(resultados)))
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(ERRO_DE_AMBIENTE.format(ambiente), file=sys.stderr)
        sys.exit(2)
