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
       "escolheu. A escolha VARIA entre rodadas — a mesma descrição não dá "
       "o mesmo placar duas vezes —, então uma volta não prova diferença "
       "nenhuma: peça --voltas e compare medianas, não rodadas. E a "
       "DERIVA entre blocos medidos em momentos diferentes é maior que a "
       "amplitude dentro de um bloco: medido em 10/09/2026, o mesmo texto "
       "deu mediana 2, 1 e 1 em três blocos de cinco voltas. Antes e "
       "depois medidos em horas diferentes não se comparam — meça os dois "
       "braços na mesma sessão de medição, ou agrupe as voltas dos dois. "
       "Quando o ganho na mediana tem o tamanho do piso do ruído, o que "
       "prova o efeito é o TETO que se rompeu: zero de quinze voltas "
       "chegando ao placar cheio contra seis de quinze é prova; mediana "
       "um ponto acima, sozinha, não é. E ANTES de tudo isso: o placar é do "
       "MODELO que mediu. As mesmas descrições deram mediana 1 de 3 no "
       "modelo padrão, que é o barato, e 3 de 3 com amplitude ZERO num "
       "modelo grande, na mesma tarde; um pedido que perdeu 54 voltas no "
       "padrão ganhou as 6 do grande. Placar baixo é hipótese sobre o "
       "roteador antes de ser sobre o texto — cinco consertos de descrição "
       "foram medidos e refutados em 10/09/2026 por não se ter repetido "
       "com o modelo da sessão de verdade primeiro")

PASTA_ESPELHADA = ".claude/skills"
PASTA_FONTE = ".agents/skills"
GLOB_SKILL = "*/SKILL.md"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
SECAO_DOS_PEDIDOS = re.compile(
    r"^## Pedidos de exemplo *\n+((?:- +.+\n?)+)", re.M)
UMA_LINHA_DE_PEDIDO = re.compile(r"^- +(.+?) *$", re.M)

MODELO = "claude-haiku-4-5-20251001"
AJUDA_DO_MODELO = ("modelo que a sessão medida usa (padrão: {}); a escolha "
                   "muda com o modelo, então a medição declara o dela")
FERRAMENTA_DA_ESCOLHA = "Skill"
FALA_DE_GENTE = "user"
BLOCO_DE_TEXTO = "text"
TEMPO_DE_UMA_SESSAO = 180

VOLTAS = 1
VOLTA_MINIMA = 1
AJUDA_DAS_VOLTAS = ("quantas vezes repetir a medição inteira (padrão: {}); "
                    "acima de uma, o placar de cada skill sai por mediana e "
                    "a amplitude entre as voltas diz o piso do ruído — "
                    "diferença menor que ela não está provada")
VOLTAS_INVALIDAS = ("--voltas pede pelo menos {}: zero volta não mede, e o "
                    "que não foi medido não é zero.")

TITULO = "O GATILHO DAS DESCRIÇÕES — que skill cada pedido acordou"
LINHA_DO_PLACAR = "  {:<22} {}/{}"
LINHA_DAS_VOLTAS = "  {:<22} {}/{} na mediana — voltas {}, amplitude {}"
LINHA_DA_COLISAO = "      veio {:<18} {}"
LINHA_DA_COLISAO_EM_VOLTAS = "      veio {:<18} {} de {} voltas  {}"
LINHA_NAO_MEDIDO_EM_VOLTAS = "      NÃO MEDIDO         {} de {} voltas  {}"
MAIOR_AMPLITUDE = ("  piso do ruído: a maior amplitude foi {} (em {}) — com "
                   "{} voltas, diferença menor que essa não se prova.")
SEM_AMPLITUDE = ("  piso do ruído: nenhuma skill variou nas {} voltas — o "
                 "placar repetiu.")
SEM_NOME = ("  {}: o frontmatter não declara `name` — a skill não carrega, e "
            "medi-la devolveria zero por um motivo que não é a descrição")
NOME_DIVERGE = ("  {}: a pasta e o campo `name` divergem (`{}`) — a skill não "
                "carrega, e medi-la devolveria zero por um motivo que não é "
                "a descrição")
POR_QUE_RECUSO = ("Conserte antes de medir. Zero por skill quebrada e zero "
                  "por descrição ruim são o MESMO número, e é assim que se "
                  "conclui a causa errada.")
LINHA_SEM_PEDIDO = ("  {:<22} NÃO MEDIDA — sem a seção `## Pedidos de "
                    "exemplo` no corpo")
LINHA_NAO_MEDIDO = "      NÃO MEDIDO             {}"
LINHA_DAS_COLISOES = "  colisões: {}"
SEM_COLISAO = "  colisões: nenhuma"
LINHA_DO_TEMPO = "  tempo de parede: {:.1f} s"
SUSPEITE_DO_ROTEADOR = (
    "  placar abaixo do teto NO MODELO PADRÃO, que é o barato: repita com "
    "--modelo\n  <o da sua sessão> antes de mexer em descrição. Medido em 10/09/2026,\n"
    "  as MESMAS descrições deram mediana 1 de 3 no padrão e 3 de 3 com "
    "amplitude\n  ZERO num modelo grande — e o pedido que perdeu 54 voltas no padrão\n"
    "  ganhou as 6 do grande. Placar baixo aqui é hipótese sobre o "
    "ROTEADOR, não\n  sobre o texto: cinco consertos de descrição foram medidos e refutados\n  por não se ter olhado isto primeiro")
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
    achado = CAMPO_NOME.search(frente.group(1) + "\n")
    nome = achado.group(1).strip() if achado else ""
    bloco = SECAO_DOS_PEDIDOS.search(texto[frente.end():] + "\n")
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


def mediana(valores: list) -> float:
    ordenados = sorted(valores)
    meio = len(ordenados) // 2
    if len(ordenados) % 2:
        return float(ordenados[meio])
    return (ordenados[meio - 1] + ordenados[meio]) / 2


def amplitude(valores: list) -> int:
    return max(valores) - min(valores)


def placar_legivel(valor: float) -> str:
    return str(int(valor)) if valor == int(valor) else f"{valor:.1f}"


def linha_do_placar(nome: str, placares: list, quantos: int) -> str:
    if len(placares) == 1:
        return LINHA_DO_PLACAR.format(nome, placares[0], quantos)
    return LINHA_DAS_VOLTAS.format(
        nome, placar_legivel(mediana(placares)), quantos,
        " ".join(str(placar) for placar in placares), amplitude(placares))


def detalhes_de_uma_skill(nome: str, por_volta: list) -> list:
    contagem = {}
    for medidas in por_volta:
        for medida in medidas:
            if medida["medida"] and medida["veio"] == nome:
                continue
            chave = (medida["veio"] if medida["medida"] else "",
                     medida["pedido"])
            contagem[chave] = contagem.get(chave, 0) + 1
    voltas = len(por_volta)
    ordem = [medida["pedido"] for medida in (por_volta[0] if por_volta else [])]
    linhas = []
    for (veio, pedido), quantas in sorted(
            contagem.items(),
            key=lambda par: (ordem.index(par[0][1]) if par[0][1] in ordem
                             else len(ordem), -par[1], par[0][0])):
        if voltas == 1:
            linhas.append(LINHA_DA_COLISAO.format(veio, pedido) if veio
                          else LINHA_NAO_MEDIDO.format(pedido))
        elif veio:
            linhas.append(LINHA_DA_COLISAO_EM_VOLTAS.format(
                veio, quantas, voltas, pedido))
        else:
            linhas.append(LINHA_NAO_MEDIDO_EM_VOLTAS.format(
                quantas, voltas, pedido))
    return linhas


def linhas_de_uma_skill(nome: str, pedidos: list, por_volta: list) -> list:
    if not pedidos:
        return [LINHA_SEM_PEDIDO.format(nome)]
    placares = [acordaram(medidas) for medidas in por_volta]
    return [linha_do_placar(nome, placares, len(pedidos))] \
        + detalhes_de_uma_skill(nome, por_volta)


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


def linha_do_ruido(amplitudes: dict, voltas: int) -> str:
    maior = max(amplitudes.items(), key=lambda par: par[1], default=("", 0))
    if not maior[1]:
        return SEM_AMPLITUDE.format(voltas)
    return MAIOR_AMPLITUDE.format(maior[1], maior[0], voltas)


def desconfie_do_modelo(placares: list, quantos: int, modelo: str) -> bool:
    return bool(placares) and modelo == MODELO and mediana(placares) < quantos


def linhas_do_fecho(por_volta: list, quantos: int, amplitudes: dict,
                    parede: float, modelo: str = MODELO) -> list:
    todas = [m for medidas in por_volta for m in medidas]
    achadas = colisoes(todas)
    placares = [acordaram(medidas) for medidas in por_volta]
    linhas = [linha_do_placar("TOTAL", placares, quantos),
              LINHA_DAS_COLISOES.format(", ".join(achadas)) if achadas
              else SEM_COLISAO]
    if len(por_volta) > 1:
        linhas.append(linha_do_ruido(amplitudes, len(por_volta)))
    linhas.append(LINHA_DO_TEMPO.format(parede))
    if desconfie_do_modelo(placares, quantos, modelo):
        linhas.append(SUSPEITE_DO_ROTEADOR)
    return linhas


def relatorio(raiz: Path, escolhidas: set, modelo: str = MODELO,
              voltas: int = VOLTAS) -> int:
    declaradas = [(n, p) for n, p in skills_declaradas(raiz)
                  if not escolhidas or n in escolhidas]
    if not declaradas:
        sys.exit(SEM_SKILLS.format(PASTA_ESPELHADA, PASTA_FONTE))
    print(f"\n{TITULO}")
    print(LINHA_DO_MODELO.format(modelo))
    partida = time.monotonic()
    geral = [[] for _ in range(voltas)]
    amplitudes = {}
    sem_pedido = sum(1 for _, pedidos in declaradas if not pedidos)
    for nome, pedidos in declaradas:
        por_volta = [medir_uma_skill(raiz, nome, pedidos, modelo)
                     for _ in range(voltas)]
        for indice, medidas in enumerate(por_volta):
            geral[indice] += medidas
        if pedidos:
            amplitudes[nome] = amplitude([acordaram(m) for m in por_volta])
        for linha in linhas_de_uma_skill(nome, pedidos, por_volta):
            print(linha, flush=True)
    todas = [m for medidas in geral for m in medidas]
    for linha in linhas_do_fecho(geral, sum(len(p) for _, p in declaradas),
                                 amplitudes, time.monotonic() - partida,
                                 modelo):
        print(linha)
    if nao_medidos(todas):
        print(ACUSA_NAO_MEDIDO.format(nao_medidos(todas),
                                      TEMPO_DE_UMA_SESSAO), file=sys.stderr)
    return 1 if (colisoes(todas) or nao_medidos(todas) or sem_pedido) else 0


COM_PEDIDOS = """---
name: exemplo
description: uma skill qualquer.
---

# Exemplo

## Pedidos de exemplo

- "primeiro pedido"
- "segundo: com dois pontos"
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
    caso("os pedidos saem da seção do corpo, na ordem — o metadata da spec "
         "Agent Skills só aceita texto, não lista",
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

    linhas = linhas_de_uma_skill("verificacao-adversarial", ["p", "q"],
                                 [[acertou, colidiu]])
    caso("o placar da skill sai em acertos por pedidos",
         linhas[0].split()[-1] == "1/2")
    caso("a linha da colisão diz qual skill veio no lugar",
         "veio padrao-de-codigo" in linhas[1] and "q" in linhas[1])
    caso("skill sem pedido declarado é acusada, não somada",
         "NÃO MEDIDA" in linhas_de_uma_skill("pelada", [], [])[0])

    caso("a mediana de voltas ímpares é o valor do meio, não a média — "
         "média deixa uma volta atípica mexer no veredito",
         mediana([1, 3, 1, 3, 2]) == 2.0)
    caso("a mediana de voltas pares fica entre as duas do meio",
         mediana([0, 1, 2, 3]) == 1.5)
    caso("mediana de uma volta só é a própria volta", mediana([2]) == 2.0)
    caso("a amplitude é o piso do ruído — quanto o mesmo texto variou sem "
         "ninguém mexer nele",
         amplitude([1, 3, 1, 3, 2]) == 2)
    caso("placar redondo sai sem casa decimal", placar_legivel(2.0) == "2")
    caso("placar de mediana par mostra a meia unidade",
         placar_legivel(1.5) == "1.5")

    voltas_iguais = [[acertou, acertou], [acertou, acertou]]
    voltas_tortas = [[acertou, acertou], [acertou, colidiu]]
    caso("uma volta só imprime o placar cru, sem mediana nem amplitude — "
         "mediana de uma medição é a própria medição, e anunciá-la mentiria "
         "sobre ter repetido",
         "mediana" not in linha_do_placar("x", [1], 2))
    caso("acima de uma volta o placar sai por mediana",
         "1/2 na mediana" in linha_do_placar("x", [1, 1, 2], 2))
    caso("o placar de cada volta aparece ao lado da mediana, para ninguém "
         "ter de confiar nela às cegas",
         "voltas 1 1 2" in linha_do_placar("x", [1, 1, 2], 2))
    caso("a amplitude entra na linha do placar",
         "amplitude 1" in linha_do_placar("x", [1, 1, 2], 2))
    caso("colisão que se repete em todas as voltas conta quantas foram",
         any("2 de 2 voltas" in linha for linha
             in detalhes_de_uma_skill("verificacao-adversarial",
                                      [[colidiu], [colidiu]])))
    caso("colisão que só apareceu numa volta é contada como uma, não como "
         "regra — é assim que se separa achado de ruído",
         any("1 de 2 voltas" in linha for linha
             in detalhes_de_uma_skill("verificacao-adversarial",
                                      voltas_tortas)))
    caso("pedido não medido em voltas também diz em quantas",
         any("1 de 2 voltas" in linha for linha
             in detalhes_de_uma_skill("verificacao-adversarial",
                                      [[morreu], [acertou]])))
    caso("volta em que a skill acordou não vira linha de detalhe",
         detalhes_de_uma_skill("verificacao-adversarial", voltas_iguais) == [])
    outra_ladra = {"skill": "verificacao-adversarial", "pedido": "q",
                   "veio": "buscar-no-acervo", "medida": True}
    terceiro = {"skill": "verificacao-adversarial", "pedido": "r",
                "veio": "portao", "medida": True}
    detalhes = detalhes_de_uma_skill(
        "verificacao-adversarial",
        [[colidiu, terceiro], [colidiu, terceiro], [outra_ladra, terceiro]])
    caso("as linhas do mesmo pedido saem juntas, na ordem em que a skill "
         "declarou os pedidos — pedido espalhado pela lista esconde quem o "
         "rouba",
         [linha.split()[-1] for linha in detalhes] == ["q", "q", "r"])
    caso("dentro de um pedido, a skill que mais roubou vem primeiro",
         "padrao-de-codigo" in detalhes[0]
         and "buscar-no-acervo" in detalhes[1])

    fecho = linhas_do_fecho([[acertou, colidiu]], 2, {}, 1.0)
    caso("o fecho conta o total de pedidos", "1/2" in fecho[0])
    caso("o fecho lista a colisão achada", "verificacao-adversarial→padrao-de-codigo (1)" in fecho[1])
    caso("sem colisão o fecho diz nenhuma",
         SEM_COLISAO == linhas_do_fecho([[acertou]], 1, {}, 1.0)[1])
    caso("com uma volta o fecho não fala de ruído — não houve repetição que "
         "medisse ruído nenhum",
         not any("piso do ruído" in linha for linha in fecho))
    em_voltas = linhas_do_fecho(voltas_tortas, 2, {"a": 0, "b": 1}, 1.0)
    caso("acima de uma volta o fecho anuncia o piso do ruído, com a skill "
         "que mais variou",
         "amplitude foi 1 (em b)" in em_voltas[2])
    caso("placar que repetiu em todas as voltas é dito como tal, e não "
         "vira amplitude inventada",
         SEM_AMPLITUDE.format(2)
         == linhas_do_fecho(voltas_iguais, 2, {"a": 0}, 1.0)[2])

    caso("a bandeira das voltas nasce em uma — quem não pediu repetição "
         "recebe a medição de sempre",
         VOLTAS == 1 and VOLTA_MINIMA == 1)
    caso("o uso do instrumento avisa que uma volta não prova diferença",
         "--voltas" in USO)

    abaixo = linhas_do_fecho(voltas_tortas, 2, {"a": 0, "b": 1}, 1.0)
    caso("placar abaixo do teto no modelo padrão manda repetir com o modelo "
         "da sessão antes de mexer em texto",
         abaixo[-1] == SUSPEITE_DO_ROTEADOR)
    caso("no teto, o fecho não desconfia do roteador — não há o que explicar",
         not any(linha == SUSPEITE_DO_ROTEADOR
                 for linha in linhas_do_fecho(voltas_iguais, 1, {"a": 0}, 1.0)))
    caso("modelo declarado pela mão não recebe o aviso: quem escolheu o "
         "modelo já sabe qual roteador está medindo",
         not any(linha == SUSPEITE_DO_ROTEADOR
                 for linha in linhas_do_fecho(voltas_tortas, 2, {"a": 0}, 1.0,
                                              "claude-sonnet-5")))
    caso("o uso do instrumento diz que o placar é do modelo que mediu",
         "roteador antes de ser sobre o texto" in USO)

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
    ap.add_argument("--voltas", type=int, default=VOLTAS,
                    help=AJUDA_DAS_VOLTAS.format(VOLTAS))
    a = ap.parse_args()
    if a.voltas < VOLTA_MINIMA:
        sys.exit(VOLTAS_INVALIDAS.format(VOLTA_MINIMA))
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
    return relatorio(raiz, set(a.skill), a.modelo, a.voltas)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
