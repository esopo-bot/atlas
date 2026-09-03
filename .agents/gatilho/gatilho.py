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
AJUDA_DO_MODELO = ("modelo que a sessão medida usa (padrão: {}); a escolha "
                   "muda com o modelo, então a medição declara o dela")
FERRAMENTA_DA_ESCOLHA = "Skill"
FALA_DE_GENTE = "user"
BLOCO_DE_TEXTO = "text"
TEMPO_DE_UMA_SESSAO = 180

TITULO = "O GATILHO DAS DESCRIÇÕES — que skill cada pedido acordou"
LINHA_DO_PLACAR = "  {:<22} {}/{}"
LINHA_DA_COLISAO = "      veio {:<18} {}"
SEM_NOME = ("  {}: o frontmatter não declara `name` — a skill não carrega, e "
            "medi-la devolveria zero por um motivo que não é a descrição")
NOME_DIVERGE = ("  {}: a pasta e o campo `name` divergem (`{}`) — a skill não "
                "carrega, e medi-la devolveria zero por um motivo que não é "
                "a descrição")
POR_QUE_RECUSO = ("Conserte antes de medir. Zero por skill quebrada e zero "
                  "por descrição ruim são o MESMO número, e é assim que se "
                  "conclui a causa errada.")
LINHA_SEM_PEDIDO = ("  {:<22} NÃO MEDIDA — sem pedidos-de-exemplo no "
                    "frontmatter")
LINHA_NAO_MEDIDO = "      NÃO MEDIDO             {}"
LINHA_DAS_COLISOES = "  colisões: {}"
SEM_COLISAO = "  colisões: nenhuma"
LINHA_DO_TEMPO = "  tempo de parede: {:.1f} s"
LINHA_DO_MODELO = "  modelo: {}"
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


def skills_que_nao_carregam(raiz: Path) -> list:
    achados = []
    for skill in sorted(pasta_das_skills(raiz).glob(GLOB_SKILL)):
        pasta = skill.parent.name
        nome, _ = nome_e_pedidos(skill.read_text(encoding="utf-8"))
        if not nome:
            achados.append(SEM_NOME.format(pasta))
        elif nome != pasta:
            achados.append(NOME_DIVERGE.format(pasta, nome))
    return achados


def comando_da_sessao(pedido: str, modelo: str = MODELO) -> list:
    return ["claude", "-p", pedido, "--output-format", "stream-json",
            "--verbose", "--model", modelo,
            "--tools", FERRAMENTA_DA_ESCOLHA,
            "--strict-mcp-config", "--setting-sources", "project"]


def evento_da_linha(linha: str) -> dict:
    try:
        evento = json.loads(linha)
    except ValueError:
        return {}
    return evento if isinstance(evento, dict) else {}


def turno_do_pedido_acabou(linha: str) -> bool:
    evento = evento_da_linha(linha)
    if evento.get("type") != FALA_DE_GENTE:
        return False
    mensagem = evento.get("message") or {}
    return any(isinstance(bloco, dict) and bloco.get("type") == BLOCO_DE_TEXTO
               for bloco in (mensagem.get("content") or []))


def skill_da_linha(linha: str):
    evento = evento_da_linha(linha)
    if evento.get("type") != "assistant":
        return None
    mensagem = evento.get("message") or {}
    for bloco in (mensagem.get("content") or []):
        if isinstance(bloco, dict) \
                and bloco.get("name") == FERRAMENTA_DA_ESCOLHA:
            return (bloco.get("input") or {}).get("skill")
    return None


def escolha_da_sessao(raiz: Path, pedido: str, modelo: str = MODELO) -> tuple:
    processo = subprocess.Popen(
        comando_da_sessao(pedido, modelo), cwd=raiz, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    estourou = []

    def matar():
        estourou.append(True)
        processo.kill()

    carrasco = threading.Timer(TEMPO_DE_UMA_SESSAO, matar)
    carrasco.start()
    escolhida = None
    turno_acabou = False
    try:
        for linha in processo.stdout:
            turno_acabou = turno_do_pedido_acabou(linha)
            if turno_acabou:
                break
            escolhida = skill_da_linha(linha)
            if escolhida:
                break
    finally:
        carrasco.cancel()
        processo.kill()
        processo.wait()
    if escolhida:
        return escolhida, True
    return NENHUMA, turno_acabou or (not estourou and processo.returncode == 0)


def medir_uma_skill(raiz: Path, nome: str, pedidos: list,
                    modelo: str = MODELO) -> list:
    medidas = []
    for pedido in pedidos:
        veio, medida = escolha_da_sessao(raiz, pedido, modelo)
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


def relatorio(raiz: Path, escolhidas: set, modelo: str = MODELO) -> int:
    declaradas = [(n, p) for n, p in skills_declaradas(raiz)
                  if not escolhidas or n in escolhidas]
    if not declaradas:
        sys.exit(SEM_SKILLS.format(PASTA_ESPELHADA, PASTA_FONTE))
    print(f"\n{TITULO}")
    print(LINHA_DO_MODELO.format(modelo))
    partida = time.monotonic()
    todas = []
    sem_pedido = sum(1 for _, pedidos in declaradas if not pedidos)
    for nome, pedidos in declaradas:
        medidas = medir_uma_skill(raiz, nome, pedidos, modelo)
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
                              "input": {"skill": "verificacao-adversarial"}}]}})
FALA_DO_GANCHO_DE_PARADA = json.dumps(
    {"type": "user",
     "message": {"content": [{"type": "text",
                              "text": "Stop hook feedback: ..."}]}})
FALA_DE_OUTRO_GANCHO = json.dumps(
    {"type": "system", "subtype": "hook_started",
     "hook_event": "SessionStart"})
RESPOSTA_DE_FERRAMENTA = json.dumps(
    {"type": "user",
     "message": {"content": [{"type": "tool_result", "content": "ok"}]}})
FALA_DE_TEXTO = json.dumps(
    {"type": "assistant",
     "message": {"content": [{"type": "text", "text": "oi"}]}})


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        espelho = raiz / PASTA_ESPELHADA
        for nome_da_pasta, declarado in (("boa", "boa"), ("torta", "outra"),
                                         ("muda", None)):
            alvo = espelho / nome_da_pasta
            alvo.mkdir(parents=True)
            cabeca = f"name: {declarado}\n" if declarado else ""
            (alvo / "SKILL.md").write_text(
                f"---\n{cabeca}description: x\n---\n", encoding="utf-8")
        quebradas = skills_que_nao_carregam(raiz)
        caso("skill com pasta e `name` divergentes é recusada, não medida — "
             "zero por skill quebrada e zero por descrição ruim são o mesmo "
             "número",
             any("torta" in linha for linha in quebradas))
        caso("skill sem `name` no frontmatter também é recusada",
             any("muda" in linha for linha in quebradas))
        caso("skill inteira não entra na lista de recusadas",
             not any("boa" in linha for linha in quebradas))

    nome, pedidos = nome_e_pedidos(COM_PEDIDOS)
    caso("o nome da skill sai do frontmatter", nome == "exemplo")
    caso("os pedidos saem do metadata, na ordem",
         pedidos == ["primeiro pedido", "segundo: com dois pontos"])
    caso("skill sem pedidos devolve lista vazia, não erro",
         nome_e_pedidos(SEM_PEDIDOS) == ("pelada", []))
    caso("texto sem frontmatter não vira skill",
         nome_e_pedidos("# só corpo\n") == ("", []))

    caso("a chamada da ferramenta Skill entrega a skill escolhida",
         skill_da_linha(FALA_DE_ESCOLHA) == "verificacao-adversarial")
    caso("fala sem chamada de ferramenta não escolhe skill",
         skill_da_linha(FALA_DE_TEXTO) is None)
    caso("linha que não é JSON não escolhe skill",
         skill_da_linha("carregando...\n") is None)
    caso("a cobrança do gancho de parada chega como fala de gente e encerra "
         "o turno do pedido — o que a sessão escolher depois dela responde "
         "à cobrança, não ao pedido",
         turno_do_pedido_acabou(FALA_DO_GANCHO_DE_PARADA))
    caso("resposta de ferramenta não encerra o turno",
         not turno_do_pedido_acabou(RESPOSTA_DE_FERRAMENTA))
    caso("gancho de abertura não encerra o turno",
         not turno_do_pedido_acabou(FALA_DE_OUTRO_GANCHO))
    caso("fala do modelo não encerra o turno",
         not turno_do_pedido_acabou(FALA_DE_ESCOLHA))

    caso("o pedido vai inteiro para a linha de comando",
         "meu pedido" in comando_da_sessao("meu pedido"))
    caso("o modelo pedido vai para a linha de comando da sessão",
         "claude-sonnet-5" in comando_da_sessao("x", "claude-sonnet-5"))
    caso("sem modelo pedido, a sessão usa o padrão",
         MODELO in comando_da_sessao("x"))
    caso("a sessão medida só recebe a ferramenta da escolha",
         comando_da_sessao("x").count(FERRAMENTA_DA_ESCOLHA) == 1)

    acertou = {"skill": "verificacao-adversarial", "pedido": "p", "veio": "verificacao-adversarial",
               "medida": True}
    colidiu = {"skill": "verificacao-adversarial", "pedido": "q", "veio": "padrao-de-codigo",
               "medida": True}
    morreu = {"skill": "verificacao-adversarial", "pedido": "r", "veio": NENHUMA,
              "medida": False}
    caso("só conta quem acordou a própria skill",
         acordaram([acertou, colidiu]) == 1)
    caso("pedido não medido não conta como acerto",
         acordaram([morreu]) == 0)
    caso("a colisão nomeia quem veio no lugar",
         colisoes([colidiu]) == ["verificacao-adversarial→padrao-de-codigo (1)"])
    caso("a mesma colisão duas vezes vira uma linha com a contagem",
         colisoes([colidiu, colidiu]) == ["verificacao-adversarial→padrao-de-codigo (2)"])
    caso("pedido que acordou a própria skill não vira colisão",
         colisoes([acertou]) == [])
    caso("pedido não medido não vira colisão",
         colisoes([morreu]) == [])
    caso("pedido não medido é contado à parte", nao_medidos([morreu]) == 1)

    linhas = linhas_de_uma_skill("verificacao-adversarial", ["p", "q"], [acertou, colidiu])
    caso("o placar da skill sai em acertos por pedidos",
         linhas[0].split()[-1] == "1/2")
    caso("a linha da colisão diz qual skill veio no lugar",
         "veio padrao-de-codigo" in linhas[1] and "q" in linhas[1])
    caso("skill sem pedido declarado é acusada, não somada",
         "NÃO MEDIDA" in linhas_de_uma_skill("pelada", [], [])[0])

    fecho = linhas_do_fecho([acertou, colidiu], 1.0)
    caso("o fecho conta o total de pedidos", "1/2" in fecho[0])
    caso("o fecho lista a colisão achada", "verificacao-adversarial→padrao-de-codigo (1)" in fecho[1])
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
    ap.add_argument("--modelo", default=MODELO,
                    help=AJUDA_DO_MODELO.format(MODELO))
    a = ap.parse_args()
    raiz = Path.cwd()
    if (quebradas := skills_que_nao_carregam(raiz)):
        for linha in quebradas:
            print(linha, file=sys.stderr)
        print(POR_QUE_RECUSO, file=sys.stderr)
        return 2
    existentes = [n for n, _ in skills_declaradas(raiz)]
    for pedida in a.skill:
        if pedida not in existentes:
            sys.exit(SKILL_DESCONHECIDA.format(pedida, " ".join(existentes)))
    if not shutil.which("claude"):
        print(SEM_CLAUDE, file=sys.stderr)
        return 1
    return relatorio(raiz, set(a.skill), a.modelo)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
