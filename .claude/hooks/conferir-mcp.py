"""Gancho SessionStart: acusa declaração de MCP apontando para arquivo que não existe.

Servidor MCP declarado que não sobe some da lista de ferramentas. No Claude
Code atual a falha de conexão chega ao agente (status no `claude mcp list`
e aviso quando a busca de ferramenta não acha); em outros agentes o sumiço
é silencioso. Este gancho acusa ANTES do uso e cobre os agentes que calam.

A causa mais comum é caminho morto: o `command`, um item de `args` ou o
ajudante de cabeçalho apontam para um arquivo que mudou de lugar, nunca foi
commitado, ou ficou para trás quando a raiz do repositório mudou de nome.
Ninguém valida esses caminhos na declaração — este gancho valida na abertura.

Ele confere só o que dá para provar barato: caminho declarado existe no
disco? Não sobe servidor nem fala protocolo — a sonda completa é assunto da
página conhecimento/mcp.md. E cala quando está tudo lá: aviso que aparece
sempre ensina a ignorar aviso.

Rode os testes com:  python .claude/hooks/conferir-mcp.py --testar
"""

import json
import os
import shlex
import sys
from pathlib import Path

# Extensões que denunciam arquivo executável ou script. Token sem separador e
# sem extensão destas é programa do PATH ("python", "node") ou argumento
# comum ("run", "-m") — não é caminho para conferir.
EXTENSOES = {".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".ps1", ".cmd",
             ".bat", ".exe", ".jar", ".rb", ".php"}


def parece_caminho(token: str) -> bool:
    """Só o que dá para conferir sem adivinhar.

    Fica de fora: bandeira, URL, variável não resolvida (`${VAR}`), curinga e
    pacote npm com escopo (`@scope/nome` tem barra e não é arquivo).
    """
    if not token or token.startswith(("-", "@")):
        return False
    if "${" in token or "://" in token or "*" in token:
        return False
    if any(token.lower().endswith(e) for e in EXTENSOES):
        return True
    return "/" in token or "\\" in token


def tokens_do_comando(texto: str) -> list:
    try:
        return shlex.split(texto, posix=False)
    except ValueError:
        return texto.split()


def candidatos_do_servidor(servidor: dict) -> list:
    """Todos os tokens de caminho que uma declaração pode carregar."""
    tokens = []
    comando = servidor.get("command", "")
    if isinstance(comando, str) and comando:
        tokens += tokens_do_comando(comando)
    args = servidor.get("args", [])
    if isinstance(args, list):
        tokens += [a for a in args if isinstance(a, str)]
    ajudante = servidor.get("headersHelper", "")
    if isinstance(ajudante, str) and ajudante:
        tokens += tokens_do_comando(ajudante)
    return [t.strip('"') for t in tokens if isinstance(t, str)]


def faltantes(cfg: dict, raiz: Path) -> list:
    """Pares (servidor, caminho) declarados e ausentes do disco."""
    problemas = []
    for nome, servidor in cfg.get("mcpServers", {}).items():
        if not isinstance(servidor, dict):
            continue
        for token in candidatos_do_servidor(servidor):
            if not parece_caminho(token):
                continue
            caminho = Path(token.replace("\\", "/"))
            alvo = caminho if caminho.is_absolute() else raiz / caminho
            if not alvo.exists():
                problemas.append((nome, token))
    return problemas


def main() -> int:
    # O cwd anda com a sessão; a raiz do projeto, não. A variável vem do
    # Claude Code; sem ela, o próprio arquivo sabe onde mora — nunca o cwd.
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    raiz = Path(base) if base else Path(__file__).resolve().parents[2]
    arquivo = raiz / ".mcp.json"
    if not arquivo.exists():
        return 0  # nada declarado, nada a conferir

    try:
        cfg = json.loads(arquivo.read_text(encoding="utf-8"))
        problemas = faltantes(cfg, raiz)
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return 0  # falha aberto: gancho quebrado não prende a sessão

    if not problemas:
        return 0  # tudo no lugar é silêncio

    linhas = [f"- servidor `{nome}`: `{caminho}` não existe no disco"
              for nome, caminho in problemas]
    aviso = (
        "AVISO do gancho conferir-mcp: o .mcp.json declara caminho que não "
        "existe. O servidor não vai subir e o sintoma é silencioso — ele "
        "some da lista de ferramentas como se nunca tivesse sido "
        "configurado.\n" + "\n".join(linhas) + "\n"
        "Avise o dono antes de precisar da ferramenta, não depois de ela "
        "faltar."
    )
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": aviso,
    }}))
    return 0


# --- Testes -----------------------------------------------------------------
# Duas listas, e a segunda é a que importa: aviso que dispara à toa é
# desligado na primeira semana. Metade dos casos prova que ele CALA.

def testar() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        (raiz / "existe").mkdir()
        (raiz / "existe/servidor.py").write_text("", encoding="utf-8")
        absoluto = str(raiz / "existe/servidor.py")

        ACUSA = [
            ("arg relativo que sumiu",
             {"command": "python", "args": [".agents/mcp/x/servidor.py"]}),
            ("ajudante de cabeçalho ausente",
             {"type": "http", "url": "https://exemplo.com/mcp",
              "headersHelper": "python .claude/servidor/cabecalho.py"}),
            ("o próprio command é caminho morto",
             {"command": "./bin/servidor.exe"}),
            ("caminho com barra invertida",
             {"command": "python", "args": ["pasta\\faltante.py"]}),
            ("caminho absoluto que não existe",
             {"command": "python", "args": [absoluto + ".sumiu"]}),
        ]

        CALA = [
            ("arquivo relativo que existe",
             {"command": "python", "args": ["existe/servidor.py"]}),
            ("programa do PATH com módulo",
             {"command": "python", "args": ["-m", "modulo.qualquer"]}),
            ("pacote npm com escopo não é arquivo",
             {"command": "npx", "args": ["-y", "@escopo/pacote-mcp"]}),
            ("servidor http sem caminho nenhum",
             {"type": "http", "url": "https://exemplo.com/mcp",
              "headers": {"Authorization": "Bearer ${TOKEN}"}}),
            ("variável não resolvida fica de fora",
             {"command": "python", "args": ["${CAMINHO}/servidor.py"]}),
            ("caminho absoluto que existe",
             {"command": "python", "args": [absoluto]}),
        ]

        falhas = []
        for rotulo, servidor in ACUSA:
            if not faltantes({"mcpServers": {"s": servidor}}, raiz):
                falhas.append(f"  DEVIA ACUSAR e calou — {rotulo}")
        for rotulo, servidor in CALA:
            achou = faltantes({"mcpServers": {"s": servidor}}, raiz)
            if achou:
                falhas.append(f"  DEVIA CALAR e acusou — {rotulo}: {achou}")

        total = len(ACUSA) + len(CALA)
        if falhas:
            print(f"FALHOU: {len(falhas)} de {total} casos")
            print("\n".join(falhas))
            return 1
        print(f"OK: {total} casos — {len(ACUSA)} acusados, {len(CALA)} calados")
        return 0


if __name__ == "__main__":
    sys.exit(testar() if "--testar" in sys.argv else main())
