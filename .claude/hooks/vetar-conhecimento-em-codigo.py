#!/usr/bin/env python3
"""Impede que conhecimento nasça em diretório que só guarda código.

O PORQUÊ: num workspace, o diretório dos repositórios é território do
código. Nota, análise e anotação que aparecem lá se perdem — ninguém as
procura ali, e elas viajam por engano no commit do repositório errado.
Conhecimento tem endereço próprio, e este gancho é a cerca desse endereço.

A RÉGUA — o `.git` é a fronteira, e o alvo é conhecimento NASCENDO no lugar
errado, nunca edição do que já existe:

| Ação                                              | Veredito |
| ------------------------------------------------- | -------- |
| criar `.md`/`.txt` na raiz do diretório declarado | barra    |
| criar `.md`/`.txt` em subpasta SEM `.git`         | barra    |
| criar ou editar `.md` DENTRO de repositório git   | passa    |
| qualquer arquivo de código, em qualquer lugar     | passa    |
| editar `.md`/`.txt` que já existe                 | passa    |

Dentro de um repositório, README e docs são do repositório: quem julga é o
fluxo de revisão dele, não este gancho.

DE ONDE VEM A LISTA: `nucleo/executor.json`, campo `diretorios_so_codigo` —
arquivo local, que não viaja. **Sem configuração, tudo passa**: repositório
que não declarou nada não ganha cerca de fantasma.

DUAS PORTAS, porque uma só deixaria a outra aberta: as ferramentas de
escrita (Write, Edit) e o shell (`echo > nota.md`, `tee`, heredoc). Fora das
ferramentas do agente — um editor aberto à mão — nada impede, e isso está
dito aqui em vez de prometido.

Falha ABERTO: entrada quebrada ou configuração ilegível não prendem a
sessão. Gancho que trava o trabalho por defeito próprio é desligado na
primeira semana.

Rode os testes com:  python .claude/hooks/vetar-conhecimento-em-codigo.py --testar
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

ARQUIVO_EXECUTOR = "nucleo/executor.json"
# O que conta como conhecimento. Configurável por `extensoes_de_conhecimento`
# no mesmo arquivo; estes são o padrão.
EXTENSOES = (".md", ".txt")

# Redirecionamento e escrita por shell: `> nota.md`, `>> nota.md`, e os
# comandos que gravam sem seta. Sem isto, o veto das ferramentas seria
# contornado por `bash -c` — e um veto contornável é pior que nenhum,
# porque promete o que não cumpre.
_REDIRECIONA = re.compile(r">>?\s*([^\s;|&]+)")
_ESCREVEM = ("tee", "cp", "mv", "install", "touch")


def _configuracao(raiz: Path):
    """{diretorios, extensoes} do executor.json, ou None se não há."""
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dado, dict):
        return None
    diretorios = [d for d in (dado.get("diretorios_so_codigo") or [])
                  if isinstance(d, str) and d.strip()
                  and "${" not in d]
    if not diretorios:
        return None
    extensoes = tuple(dado.get("extensoes_de_conhecimento") or EXTENSOES)
    return {"diretorios": diretorios, "extensoes": extensoes}


def _e_conhecimento(caminho: str, extensoes) -> bool:
    return caminho.lower().endswith(tuple(e.lower() for e in extensoes))


def _dentro_de_repositorio(alvo: Path, fronteira: Path) -> bool:
    """Há um `.git` entre o arquivo e o diretório declarado?

    Sobe do arquivo até a fronteira, sem passar dela: repositório clonado
    lá dentro é território do fluxo de revisão dele, não deste gancho.
    """
    atual = alvo.parent
    while True:
        if (atual / ".git").exists():
            return True
        if atual == fronteira or atual.parent == atual:
            return False
        atual = atual.parent


def motivo_da_recusa(caminho: str, raiz: Path, configuracao) -> str:
    """A recusa, ou '' quando passa."""
    if not configuracao or not caminho:
        return ""
    if not _e_conhecimento(caminho, configuracao["extensoes"]):
        return ""
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = (raiz / alvo)
    try:
        alvo = alvo.resolve(strict=False)
    except OSError:
        return ""
    if alvo.exists():
        return ""  # editar o que já existe não é fazer nascer no lugar errado
    for declarado in configuracao["diretorios"]:
        fronteira = (raiz / declarado).resolve(strict=False) \
            if not Path(declarado).is_absolute() else Path(declarado).resolve()
        if not fronteira.is_dir():
            continue
        if fronteira not in alvo.parents:
            continue
        if _dentro_de_repositorio(alvo, fronteira):
            return ""  # é do repositório; o fluxo dele julga
        return (f"criar {alvo.name!r} em {declarado!r}, que a configuração "
                "declara como diretório só de código")
    return ""


def alvos_do_pedido(entrada: dict) -> list:
    """Todo caminho que este pedido tentaria criar."""
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in ("Write", "Edit", "NotebookEdit"):
        caminho = dado.get("file_path") or dado.get("notebook_path") or ""
        return [caminho] if caminho else []
    comando = dado.get("command", "")
    if not comando:
        return []
    achados = [m.group(1) for m in _REDIRECIONA.finditer(comando)]
    try:
        pedacos = shlex.split(comando)
    except ValueError:
        pedacos = comando.split()
    if pedacos and Path(pedacos[0]).name in _ESCREVEM:
        achados += pedacos[1:]
    return [a.strip("\"'") for a in achados if a and not a.startswith("-")]


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return 0  # falha aberto: entrada quebrada não prende a sessão

    base = os.environ.get("CLAUDE_PROJECT_DIR")
    raiz = Path(base) if base else Path(__file__).resolve().parents[2]
    configuracao = _configuracao(raiz)
    if not configuracao:
        return 0  # sem declaração, sem cerca

    for caminho in alvos_do_pedido(entrada):
        motivo = motivo_da_recusa(caminho, raiz, configuracao)
        if motivo:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Isto quer {motivo}. Conhecimento não nasce em pasta de "
                    "código: lá ninguém o procura, e ele viaja por engano no "
                    "commit do repositório errado. Escreva em "
                    "`conhecimento/`, ou — se o texto é DAQUELE repositório "
                    "(README, docs/) — crie dentro dele, que o fluxo de "
                    "revisão dele julga. Para mudar a cerca: "
                    f"`diretorios_so_codigo` em {ARQUIVO_EXECUTOR}."
                ),
            }}))
            return 0
    return 0


# --- Testes -----------------------------------------------------------------
# Duas listas, e a segunda é a que importa: veto largo é desligado na
# primeira semana. Metade dos casos existe para provar que ele NÃO atrapalha.

def _cenario(pasta: Path):
    """Um workspace de mentira: projetos/ declarado, um repo git dentro."""
    (pasta / "nucleo").mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo" / "executor.json").write_text(json.dumps({
        "diretorios_so_codigo": ["projetos"]}), encoding="utf-8")
    (pasta / "projetos" / "app" / ".git").mkdir(parents=True, exist_ok=True)
    (pasta / "projetos" / "solta").mkdir(parents=True, exist_ok=True)
    (pasta / "projetos" / "ja-existe.md").write_text("velho", encoding="utf-8")
    (pasta / "conhecimento").mkdir(exist_ok=True)
    return _configuracao(pasta)


BARRA = [
    ("nota na raiz do diretório declarado", "projetos/nota.md"),
    ("texto na raiz do diretório declarado", "projetos/rascunho.txt"),
    ("nota em subpasta que não é repositório", "projetos/solta/ideia.md"),
]

DEIXA_PASSAR = [
    ("README dentro de um repositório", "projetos/app/README.md"),
    ("doc dentro de um repositório", "projetos/app/docs/uso.md"),
    ("código no diretório declarado", "projetos/solta/main.py"),
    ("nota fora do diretório declarado", "conhecimento/nota.md"),
    ("arquivo de conhecimento que JÁ EXISTE", "projetos/ja-existe.md"),
]


def testar() -> int:
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory(prefix="veto-conhecimento-") as tmp:
        raiz = Path(tmp)
        configuracao = _cenario(raiz)
        for rotulo, caminho in BARRA:
            if not motivo_da_recusa(caminho, raiz, configuracao):
                falhas.append(f"BARRA [{rotulo}]: deixou passar")
        for rotulo, caminho in DEIXA_PASSAR:
            motivo = motivo_da_recusa(caminho, raiz, configuracao)
            if motivo:
                falhas.append(f"DEIXA_PASSAR [{rotulo}]: barrou — {motivo}")

        comportamento = []

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        # sem configuração, nada é barrado
        caso("sem executor.json a cerca não existe",
             not motivo_da_recusa("projetos/nota.md", raiz, None))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps({
            "diretorios_so_codigo": ["${DIRETORIO}"]}), encoding="utf-8")
        caso("diretório ainda no molde não vira cerca",
             _configuracao(raiz) is None)
        _cenario(raiz)

        # a porta do shell
        caso("redirecionamento por shell é alcançado",
             alvos_do_pedido({"tool_name": "Bash", "tool_input": {
                 "command": "echo oi > projetos/nota.md"}})
             == ["projetos/nota.md"])
        caso("append também",
             "projetos/n.md" in alvos_do_pedido({"tool_name": "Bash",
                 "tool_input": {"command": "echo a >> projetos/n.md"}}))
        caso("tee também",
             "projetos/t.md" in alvos_do_pedido({"tool_name": "Bash",
                 "tool_input": {"command": "tee projetos/t.md"}}))
        caso("a ferramenta Write é alcançada",
             alvos_do_pedido({"tool_name": "Write", "tool_input": {
                 "file_path": "projetos/nota.md"}}) == ["projetos/nota.md"])
        caso("comando sem escrita nenhuma não devolve alvo",
             alvos_do_pedido({"tool_name": "Bash",
                              "tool_input": {"command": "ls projetos"}}) == [])
        caso("entrada quebrada não prende a sessão (falha aberto)",
             alvos_do_pedido({}) == [])
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(alvos_do_pedido({"tool_name": "Bash", "tool_input": {
                 "command": "echo 'sem fechar > projetos/x.md"}}), list))
        falhas += [f"COMPORTAMENTO [{r}]" for r, ok in comportamento if not ok]

    total = len(BARRA) + len(DEIXA_PASSAR) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — {len(BARRA)} barrados, "
          f"{len(DEIXA_PASSAR)} liberados, {len(comportamento)} de "
          "comportamento")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    sys.exit(main())
