import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("mede se a descrição de cada skill dispara: abre uma sessão por "
       "pedido de exemplo declarado na skill e verifica qual skill ela "
       "escolheu")

PASTA_ESPELHADA = ".claude/skills"
PASTA_FONTE = ".agents/skills"
GLOB_SKILL = "*/SKILL.md"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
BLOCO_DOS_PEDIDOS = re.compile(
    r"^ *pedidos-de-exemplo: *\n((?: +- +.+\n)+)", re.M)
UMA_LINHA_DE_PEDIDO = re.compile(r"^ +- +(.+?) *$", re.M)

MODELO = "claude-haiku-4-5-20251001"
FERRAMENTA_DA_ESCOLHA = "Skill"
TEMPO_DE_UMA_SESSAO = 180

TITULO = "O GATILHO DAS DESCRIÇÕES — que skill cada pedido acordou"
LINHA_DO_PLACAR = "  {:<22} {}/{}"
LINHA_DA_COLISAO = "      veio {:<18} {}"
LINHA_SEM_PEDIDO = ("  {:<22} NÃO MEDIDA — sem pedidos-de-exemplo no "
                    "frontmatter")
LINHA_NAO_MEDIDO = "      NÃO MEDIDO             {}"
LINHA_DAS_COLISOES = "  colisões: {}"
SEM_COLISAO = "  colisões: nenhuma"
LINHA_DO_TEMPO = "  tempo de parede: {:.1f} s"
UMA_COLISAO = "{}→{} ({})"
NENHUMA = "nenhuma"
SEM_CLAUDE = ("NÃO MEDIDO: claude fora do PATH — sem sessão não há escolha "
              "a verificar, e zero aqui seria invenção.")
SEM_SKILLS = "Sem skills em {} nem em {} — nada a medir."
ACUSA_NAO_MEDIDO = ("NÃO MEDIDO: {} pedido(s) ficaram sem resposta — a "
                    "sessão morreu ou estourou {}s. O número que falta não "
                    "é zero.")
SKILL_DESCONHECIDA = "Skill que não existe: {}.\nAs que existem: {}."


def pasta_das_skills(raiz: Path) -> Path:
    espelhada = raiz / PASTA_ESPELHADA
    return espelhada if espelhada.is_dir() else raiz / PASTA_FONTE


def texto_do_pedido(valor: str) -> str:
    if valor[:1] == '"' == valor[-1:]:
        return valor[1:-1]
    return valor


def nome_e_pedidos(texto: str) -> tuple:
    frente = FRONTMATTER.match(texto)
    if not frente:
        return "", []
    corpo = frente.group(1) + "\n"
    achado = CAMPO_NOME.search(corpo)
    nome = achado.group(1).strip() if achado else ""
    bloco = BLOCO_DOS_PEDIDOS.search(corpo)
    if not bloco:
        return nome, []
    return nome, [texto_do_pedido(l)
                  for l in UMA_LINHA_DE_PEDIDO.findall(bloco.group(1))]


def skills_declaradas(raiz: Path) -> list:
    declaradas = []
    for skill in sorted(pasta_das_skills(raiz).glob(GLOB_SKILL)):
        nome, pedidos = nome_e_pedidos(skill.read_text(encoding="utf-8"))
        if nome:
            declaradas.append((nome, pedidos))
    return declaradas


def comando_da_sessao(pedido: str) -> list:
    return ["claude", "-p", pedido, "--output-format", "stream-json",
            "--verbose", "--model", MODELO,
            "--tools", FERRAMENTA_DA_ESCOLHA,
            "--strict-mcp-config", "--setting-sources", "project"]


def skill_da_linha(linha: str):
    try:
        evento = json.loads(linha)
    except ValueError:
        return None
    if not isinstance(evento, dict) or evento.get("type") != "assistant":
        return None
    mensagem = evento.get("message") or {}
    for bloco in (mensagem.get("content") or []):
        if isinstance(bloco, dict) \
                and bloco.get("name") == FERRAMENTA_DA_ESCOLHA:
            return (bloco.get("input") or {}).get("skill")
    return None


def escolha_da_sessao(raiz: Path, pedido: str) -> tuple:
    processo = subprocess.Popen(
        comando_da_sessao(pedido), cwd=raiz, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    estourou = []

    def matar():
        estourou.append(True)
        processo.kill()

    carrasco = threading.Timer(TEMPO_DE_UMA_SESSAO, matar)
    carrasco.start()
    escolhida = None
    try:
        for linha in processo.stdout:
            escolhida = skill_da_linha(linha)
            if escolhida:
                break
    finally:
        carrasco.cancel()
        processo.kill()
        processo.wait()
    if escolhida:
        return escolhida, True
    return NENHUMA, not estourou and processo.returncode == 0


def medir_uma_skill(raiz: Path, nome: str, pedidos: list) -> list:
    medidas = []
    for pedido in pedidos:
        veio, medida = escolha_da_sessao(raiz, pedido)
        medidas.append({"skill": nome, "pedido": pedido, "veio": veio,
                        "medida": medida})
    return medidas


def acordaram(medidas: list) -> int:
    return sum(1 for m in medidas if m["medida"] and m["veio"] == m["skill"])


def linhas_de_uma_skill(nome: str, pedidos: list, medidas: list) -> list:
    if not pedidos:
        return [LINHA_SEM_PEDIDO.format(nome)]
    linhas = [LINHA_DO_PLACAR.format(nome, acordaram(medidas), len(pedidos))]
    for medida in medidas:
        if not medida["medida"]:
            linhas.append(LINHA_NAO_MEDIDO.format(medida["pedido"]))
        elif medida["veio"] != nome:
            linhas.append(LINHA_DA_COLISAO.format(medida["veio"],
                                                  medida["pedido"]))
    return linhas


def colisoes(medidas: list) -> list:
    contagem = {}
    for medida in medidas:
        if not medida["medida"] or medida["veio"] == medida["skill"]:
            continue
        par = (medida["skill"], medida["veio"])
        contagem[par] = contagem.get(par, 0) + 1
    return [UMA_COLISAO.format(de, para, quantas)
            for (de, para), quantas in sorted(contagem.items())]


def nao_medidos(medidas: list) -> int:
    return sum(1 for m in medidas if not m["medida"])


def linhas_do_fecho(medidas: list, parede: float) -> list:
    achadas = colisoes(medidas)
    return [LINHA_DO_PLACAR.format("TOTAL", acordaram(medidas), len(medidas)),
            LINHA_DAS_COLISOES.format(", ".join(achadas)) if achadas
            else SEM_COLISAO,
            LINHA_DO_TEMPO.format(parede)]


def relatorio(raiz: Path, escolhidas: set) -> int:
    declaradas = [(n, p) for n, p in skills_declaradas(raiz)
                  if not escolhidas or n in escolhidas]
    if not declaradas:
        sys.exit(SEM_SKILLS.format(PASTA_ESPELHADA, PASTA_FONTE))
    print(f"\n{TITULO}")
    partida = time.monotonic()
    todas = []
    sem_pedido = sum(1 for _, pedidos in declaradas if not pedidos)
    for nome, pedidos in declaradas:
        medidas = medir_uma_skill(raiz, nome, pedidos)
        todas += medidas
        for linha in linhas_de_uma_skill(nome, pedidos, medidas):
            print(linha, flush=True)
    for linha in linhas_do_fecho(todas, time.monotonic() - partida):
        print(linha)
    if nao_medidos(todas):
        print(ACUSA_NAO_MEDIDO.format(nao_medidos(todas),
                                      TEMPO_DE_UMA_SESSAO), file=sys.stderr)
    return 1 if (colisoes(todas) or nao_medidos(todas) or sem_pedido) else 0


COM_PEDIDOS = """---
name: exemplo
description: uma skill qualquer.
metadata:
  pedidos-de-exemplo:
    - "primeiro pedido"
    - "segundo: com dois pontos"
---

# Exemplo
"""
SEM_PEDIDOS = """---
name: pelada
description: uma skill sem pedido nenhum.
---

# Pelada
"""
FALA_DE_ESCOLHA = json.dumps(
    {"type": "assistant",
     "message": {"content": [{"type": "tool_use", "name": "Skill",
                              "input": {"skill": "cetico"}}]}})
FALA_DE_TEXTO = json.dumps(
    {"type": "assistant",
     "message": {"content": [{"type": "text", "text": "oi"}]}})


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    nome, pedidos = nome_e_pedidos(COM_PEDIDOS)
    caso("o nome da skill sai do frontmatter", nome == "exemplo")
    caso("os pedidos saem do metadata, na ordem",
         pedidos == ["primeiro pedido", "segundo: com dois pontos"])
    caso("skill sem pedidos devolve lista vazia, não erro",
         nome_e_pedidos(SEM_PEDIDOS) == ("pelada", []))
    caso("texto sem frontmatter não vira skill",
         nome_e_pedidos("# só corpo\n") == ("", []))

    caso("a chamada da ferramenta Skill entrega a skill escolhida",
         skill_da_linha(FALA_DE_ESCOLHA) == "cetico")
    caso("fala sem chamada de ferramenta não escolhe skill",
         skill_da_linha(FALA_DE_TEXTO) is None)
    caso("linha que não é JSON não escolhe skill",
         skill_da_linha("carregando...\n") is None)

    caso("o pedido vai inteiro para a linha de comando",
         "meu pedido" in comando_da_sessao("meu pedido"))
    caso("a sessão medida só recebe a ferramenta da escolha",
         comando_da_sessao("x").count(FERRAMENTA_DA_ESCOLHA) == 1)

    acertou = {"skill": "cetico", "pedido": "p", "veio": "cetico",
               "medida": True}
    colidiu = {"skill": "cetico", "pedido": "q", "veio": "qualidade",
               "medida": True}
    morreu = {"skill": "cetico", "pedido": "r", "veio": NENHUMA,
              "medida": False}
    caso("só conta quem acordou a própria skill",
         acordaram([acertou, colidiu]) == 1)
    caso("pedido não medido não conta como acerto",
         acordaram([morreu]) == 0)
    caso("a colisão nomeia quem veio no lugar",
         colisoes([colidiu]) == ["cetico→qualidade (1)"])
    caso("a mesma colisão duas vezes vira uma linha com a contagem",
         colisoes([colidiu, colidiu]) == ["cetico→qualidade (2)"])
    caso("pedido que acordou a própria skill não vira colisão",
         colisoes([acertou]) == [])
    caso("pedido não medido não vira colisão",
         colisoes([morreu]) == [])
    caso("pedido não medido é contado à parte", nao_medidos([morreu]) == 1)

    linhas = linhas_de_uma_skill("cetico", ["p", "q"], [acertou, colidiu])
    caso("o placar da skill sai em acertos por pedidos",
         linhas[0].split()[-1] == "1/2")
    caso("a linha da colisão diz qual skill veio no lugar",
         "veio qualidade" in linhas[1] and "q" in linhas[1])
    caso("skill sem pedido declarado é acusada, não somada",
         "NÃO MEDIDA" in linhas_de_uma_skill("pelada", [], [])[0])

    fecho = linhas_do_fecho([acertou, colidiu], 1.0)
    caso("o fecho conta o total de pedidos", "1/2" in fecho[0])
    caso("o fecho lista a colisão achada", "cetico→qualidade (1)" in fecho[1])
    caso("sem colisão o fecho diz nenhuma",
         SEM_COLISAO == linhas_do_fecho([acertou], 1.0)[1])

    total = len(casos)
    if falhas:
        for falha in falhas:
            print(f"  [{falha}]")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — leitura dos pedidos, da escolha e do placar")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=USO)
    ap.add_argument("skill", nargs="*",
                    help="quais skills medir (padrão: todas)")
    a = ap.parse_args()
    raiz = Path.cwd()
    existentes = [n for n, _ in skills_declaradas(raiz)]
    for pedida in a.skill:
        if pedida not in existentes:
            sys.exit(SKILL_DESCONHECIDA.format(pedida, " ".join(existentes)))
    if not shutil.which("claude"):
        print(SEM_CLAUDE, file=sys.stderr)
        return 1
    return relatorio(raiz, set(a.skill))


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
