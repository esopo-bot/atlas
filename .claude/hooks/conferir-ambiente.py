"""Gancho SessionStart: acusa o que a máquina não tem e a casa declara precisar.

Mudança de pasta, de disco ou de máquina perde tudo o que vive fora do
repositório: variável de ambiente, perfil de CLI, ferramenta instalada. A
perda é silenciosa — nada avisa na hora; cada peça para dias depois, com
cara de defeito novo. Este gancho é o aviso que faltou, na primeira sessão.

Ele confere só o que dá para provar barato, sem abrir conteúdo nenhum: as
variáveis `${VAR}` que o .mcp.json usa existem no ambiente? O que o
ambiente.txt da raiz declara — comando, pasta, arquivo, variável — existe?
Nomes e existência, nunca valores. E cala quando está tudo lá: aviso que
aparece sempre ensina a ignorar aviso.

O ambiente.txt é do dono da casa (a atualização nunca o reescreve). Uma
exigência por linha; `#` comenta:

    receita conhecimento/notas/maquina-nova.md
    comando git
    pasta ~/.config/ferramenta-x
    arquivo scripts/preparar.sh
    variavel FERRAMENTA_X_TOKEN

O porquê está em conhecimento/estado-que-nao-viaja.md.

Rode os testes com:  python .claude/hooks/conferir-ambiente.py --testar
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

# ${VAR} exige a variável; ${VAR:-padrão} se vira sem ela — o padrão cobre a
# ausência, e acusar viraria alarme falso.
VARIAVEL = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-[^}]*)?\}")


def variaveis_exigidas(texto: str) -> list:
    """Os nomes de variável sem padrão, na ordem, sem repetição."""
    vistos, nomes = set(), []
    for nome, padrao in VARIAVEL.findall(texto):
        if padrao or nome in vistos:
            continue
        vistos.add(nome)
        nomes.append(nome)
    return nomes


def declaracoes(texto: str) -> list:
    """Pares (tipo, valor) do ambiente.txt. Linha vazia e comentário ficam de fora."""
    pares = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split(None, 1)
        if len(partes) == 2:
            pares.append((partes[0].lower(), partes[1].strip()))
    return pares


def alvo_no_disco(raiz: Path, valor: str) -> Path:
    caminho = Path(valor.replace("\\", "/")).expanduser()
    return caminho if caminho.is_absolute() else raiz / caminho


def faltas(raiz: Path, env=None, caminho_path=None) -> tuple:
    """(problemas, receita): o que falta na máquina, e a página que ensina a repor."""
    env = os.environ if env is None else env
    problemas, receita = [], None
    ja_acusadas = set()

    mcp = raiz / ".mcp.json"
    if mcp.is_file():
        for nome in variaveis_exigidas(mcp.read_text(encoding="utf-8")):
            if nome not in env:
                problemas.append(
                    f"- variável `{nome}` ausente do ambiente (o .mcp.json a usa)")
                ja_acusadas.add(nome)

    declarado = raiz / "ambiente.txt"
    if declarado.is_file():
        for tipo, valor in declaracoes(declarado.read_text(encoding="utf-8")):
            if tipo == "receita":
                receita = valor
                if not alvo_no_disco(raiz, valor).is_file():
                    problemas.append(
                        f"- a própria receita `{valor}` não existe no disco")
            elif tipo == "comando":
                if not shutil.which(valor, path=caminho_path):
                    problemas.append(f"- comando `{valor}` não está no PATH")
            elif tipo == "pasta":
                if not alvo_no_disco(raiz, valor).is_dir():
                    problemas.append(f"- pasta `{valor}` não existe")
            elif tipo == "arquivo":
                if not alvo_no_disco(raiz, valor).is_file():
                    problemas.append(f"- arquivo `{valor}` não está no disco")
            elif tipo == "variavel":
                if valor not in env and valor not in ja_acusadas:
                    problemas.append(f"- variável `{valor}` ausente do ambiente")
    return problemas, receita


def main() -> int:
    # O cwd anda com a sessão; a raiz do projeto, não. A variável vem do
    # Claude Code; sem ela (outro agente), o cwd da abertura ainda serve.
    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    try:
        problemas, receita = faltas(raiz)
    except Exception:
        return 0  # falha aberto: gancho quebrado não prende a sessão

    if not problemas:
        return 0  # tudo no lugar é silêncio

    fecho = (f"A receita para repor: {receita}" if receita else
             "Nenhuma receita declarada — a primeira linha do ambiente.txt "
             "pode apontar a página que ensina a repor (receita <página>).")
    aviso = (
        "AVISO do gancho conferir-ambiente: esta máquina não tem tudo o que "
        "a casa declara precisar. Perda de migração é silenciosa — este é o "
        "aviso que não existiu na mudança.\n" + "\n".join(problemas) + "\n"
        + fecho + "\n"
        "Avise o dono antes de precisar, não depois de faltar. Nome se "
        "confere; valor não se imprime nem se procura."
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
        caixa = raiz / "caixa-de-ferramentas"
        caixa.mkdir()
        util = caixa / "prensa-de-flores"
        util.write_text("#!/bin/sh\n", encoding="utf-8")
        util.chmod(0o755)

        (raiz / "estufa").mkdir()
        (raiz / "estufa/regras.md").write_text("", encoding="utf-8")

        ambiente = {"SINO_DE_VENTO_TOKEN": "presente"}

        def caso(mcp=None, declarado=None):
            for nome, conteudo in ((".mcp.json", mcp), ("ambiente.txt", declarado)):
                alvo = raiz / nome
                if conteudo is None:
                    alvo.unlink(missing_ok=True)
                else:
                    alvo.write_text(conteudo, encoding="utf-8")
            return faltas(raiz, env=ambiente, caminho_path=str(caixa))

        ACUSA = [
            ("variável do .mcp.json ausente",
             dict(mcp='{"x": "${TAMBOR_MAIOR}"}')),
            ("variável declarada ausente",
             dict(declarado="variavel CAIXA_DE_MUSICA\n")),
            ("comando fora do PATH",
             dict(declarado="comando regador-automatico\n")),
            ("pasta que não existe",
             dict(declarado="pasta estufa/inverno\n")),
            ("arquivo que não existe",
             dict(declarado="arquivo estufa/inventario.md\n")),
            ("receita apontando página morta",
             dict(declarado="receita cadernos/plantio.md\n")),
        ]

        CALA = [
            ("variável presente no ambiente",
             dict(mcp='{"x": "${SINO_DE_VENTO_TOKEN}"}')),
            ("variável com padrão se vira sem valor",
             dict(mcp='{"x": "${TAMBOR_MAIOR:-surdo}"}')),
            ("comando que está no PATH",
             dict(declarado="comando prensa-de-flores\n")),
            ("pasta que existe",
             dict(declarado="pasta estufa\n")),
            ("arquivo que existe",
             dict(declarado="arquivo estufa/regras.md\n")),
            ("receita que existe",
             dict(declarado="receita estufa/regras.md\n")),
            ("sem declaração nenhuma", dict()),
            ("comentário e linha vazia ignorados",
             dict(declarado="# nota da casa\n\n")),
        ]

        falhas = []
        for rotulo, kwargs in ACUSA:
            problemas, _ = caso(**kwargs)
            if not problemas:
                falhas.append(f"  DEVIA ACUSAR e calou — {rotulo}")
        for rotulo, kwargs in CALA:
            problemas, _ = caso(**kwargs)
            if problemas:
                falhas.append(f"  DEVIA CALAR e acusou — {rotulo}: {problemas}")

        total = len(ACUSA) + len(CALA)
        if falhas:
            print(f"FALHOU: {len(falhas)} de {total} casos")
            print("\n".join(falhas))
            return 1
        print(f"OK: {total} casos — {len(ACUSA)} acusados, {len(CALA)} calados")
        return 0


if __name__ == "__main__":
    sys.exit(testar() if "--testar" in sys.argv else main())
