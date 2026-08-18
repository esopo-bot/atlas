"""Gancho SessionStart: acusa o que a máquina não tem e a casa declara precisar.

Mudança de pasta, de disco ou de máquina perde tudo o que vive fora do
repositório: variável de ambiente, perfil de CLI, ferramenta instalada. A
perda é silenciosa — nada avisa na hora; cada peça para dias depois, com
cara de defeito novo. Este gancho é o aviso que faltou, na primeira sessão.

Ele confere só o que dá para provar barato, sem abrir conteúdo nenhum: as
variáveis `${VAR}` que o .mcp.json usa existem no ambiente? O que o
nucleo/ambiente.json declara — comando, pasta, arquivo, variável — existe?
Nomes e existência, nunca valores. E cala quando está tudo lá: aviso que
aparece sempre ensina a ignorar aviso.

O nucleo/ambiente.json é do dono da casa (a atualização nunca o reescreve).
Uma lista por tipo; valor solto vale por lista de um:

    {
      "receita": "conhecimento/notas/maquina-nova.md",
      "comando": ["git", "python3"],
      "pasta": ["~/.config/ferramenta-x"],
      "arquivo": ["scripts/preparar.sh"],
      "variavel": ["FERRAMENTA_X_TOKEN"]
    }

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


ARQUIVO_AMBIENTE = "nucleo/ambiente.json"
ARQUIVO_ANTIGO = "ambiente.txt"
TIPOS = ("receita", "comando", "pasta", "arquivo", "variavel")


def declaracoes(dados: dict) -> list:
    """Pares (tipo, valor) do nucleo/ambiente.json, na ordem dos TIPOS.

    Valor solto vale por lista de um — `"receita": "pagina.md"` é o caso
    comum, e exigir `["pagina.md"]` só deixaria o arquivo mais feio. O que
    não é texto fica de fora: exigência que ninguém sabe conferir não vira
    aviso, e chave desconhecida é comentário da casa, não erro.
    """
    pares = []
    for tipo in TIPOS:
        valores = dados.get(tipo) or []
        if isinstance(valores, str):
            valores = [valores]
        if not isinstance(valores, list):
            continue
        for valor in valores:
            if isinstance(valor, str) and valor.strip():
                pares.append((tipo, valor.strip()))
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

    declarado = raiz / ARQUIVO_AMBIENTE
    if declarado.is_file():
        try:
            dados = json.loads(declarado.read_text(encoding="utf-8"))
            if not isinstance(dados, dict):
                raise ValueError("o topo tem de ser um objeto")
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as erro:
            # Aqui não se cala: arquivo ilegível é a perda silenciosa que este
            # gancho existe para acusar — calar devolveria o defeito.
            problemas.append(f"- `{ARQUIVO_AMBIENTE}` ilegível ({erro}) — "
                             "nenhuma exigência da casa foi conferida")
            dados = {}
        for tipo, valor in declaracoes(dados):
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

    # A casa que montou a camada antiga tem o arquivo no endereço velho, e o
    # gancho não o lê mais. Calar aqui apagaria em silêncio o que ela declarou
    # — exatamente o defeito que este gancho existe para acusar.
    if (raiz / ARQUIVO_ANTIGO).is_file():
        problemas.append(
            f"- `{ARQUIVO_ANTIGO}` virou `{ARQUIVO_AMBIENTE}`: mova as "
            "declarações para lá — o gancho não lê mais o .txt")
    return problemas, receita


def main() -> int:
    # O cwd anda com a sessão; a raiz do projeto, não. A variável vem do
    # Claude Code; sem ela, o próprio arquivo sabe onde mora — nunca o cwd.
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    raiz = Path(base) if base else Path(__file__).resolve().parents[2]
    try:
        problemas, receita = faltas(raiz)
    except Exception:
        return 0  # falha aberto: gancho quebrado não prende a sessão

    if not problemas:
        return 0  # tudo no lugar é silêncio

    fecho = (f"A receita para repor: {receita}" if receita else
             f"Nenhuma receita declarada — a chave `receita` do "
             f"{ARQUIVO_AMBIENTE} pode apontar a página que ensina a repor.")
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

        def caso(mcp=None, declarado=None, antigo=None):
            """Monta a casa do caso e devolve o que o gancho acha nela.

            Dado vira JSON; texto vai como está — é assim que o caso do
            arquivo ilegível entra sem uma segunda porta só para ele.
            """
            for nome, conteudo in ((".mcp.json", mcp),
                                   (ARQUIVO_AMBIENTE, declarado),
                                   (ARQUIVO_ANTIGO, antigo)):
                alvo = raiz / nome
                alvo.parent.mkdir(parents=True, exist_ok=True)
                if conteudo is None:
                    alvo.unlink(missing_ok=True)
                elif isinstance(conteudo, str):
                    alvo.write_text(conteudo, encoding="utf-8")
                else:
                    alvo.write_text(json.dumps(conteudo, ensure_ascii=False),
                                    encoding="utf-8")
            return faltas(raiz, env=ambiente, caminho_path=str(caixa))

        ACUSA = [
            ("variável do .mcp.json ausente",
             dict(mcp='{"x": "${TAMBOR_MAIOR}"}')),
            ("variável declarada ausente",
             dict(declarado={"variavel": ["CAIXA_DE_MUSICA"]})),
            ("comando fora do PATH",
             dict(declarado={"comando": ["regador-automatico"]})),
            ("pasta que não existe",
             dict(declarado={"pasta": ["estufa/inverno"]})),
            ("arquivo que não existe",
             dict(declarado={"arquivo": ["estufa/inventario.md"]})),
            ("receita apontando página morta",
             dict(declarado={"receita": "cadernos/plantio.md"})),
            ("declaração ilegível não passa batido",
             dict(declarado="{quebrado")),
            ("o endereço velho ainda no disco acusa a mudança",
             dict(antigo="comando prensa-de-flores\n")),
        ]

        CALA = [
            ("variável presente no ambiente",
             dict(mcp='{"x": "${SINO_DE_VENTO_TOKEN}"}')),
            ("variável com padrão se vira sem valor",
             dict(mcp='{"x": "${TAMBOR_MAIOR:-surdo}"}')),
            ("comando que está no PATH",
             dict(declarado={"comando": ["prensa-de-flores"]})),
            ("pasta que existe",
             dict(declarado={"pasta": ["estufa"]})),
            ("arquivo que existe",
             dict(declarado={"arquivo": ["estufa/regras.md"]})),
            ("receita que existe",
             dict(declarado={"receita": "estufa/regras.md"})),
            ("sem declaração nenhuma", dict()),
            ("comentário da casa e chave desconhecida ficam de fora",
             dict(declarado={"comentario": "nota da casa", "receita": None})),
            ("lista vazia não inventa exigência",
             dict(declarado={"comando": [], "pasta": [], "variavel": []})),
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
