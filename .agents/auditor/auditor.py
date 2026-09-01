import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DESCRICAO_DA_CLI = (
    "lê a pasta de evidências de um trabalho e relata o que a execução "
    "provou, o que ela deixou por provar, e o que isso sugere")

AQUI = Path(__file__).resolve().parent
INSTRUMENTO_QUE_ANCORA = "verificar/verificar.py"


def _achar_a_camada() -> Path:
    for base in (AQUI.parent, *AQUI.parents):
        if (base / INSTRUMENTO_QUE_ANCORA).is_file():
            return base
        if (base / ".agents" / INSTRUMENTO_QUE_ANCORA).is_file():
            return base / ".agents"
    return AQUI.parent


VERIFICADOR = _achar_a_camada() / INSTRUMENTO_QUE_ANCORA
CAIXA = _achar_a_camada() / "caixa/caixa.py"
GLOB_DE_EVIDENCIA = "*.json"
NOME_DA_EVIDENCIA = re.compile(r"^(\d+)-(.+)-c(\d+)\.json$")
ACUSACAO_ROTULADA = re.compile(r"^ACUSA \[([^\]]+)\]")
PREFIXO_DA_ACUSACAO = "ACUSA "
PASTA_DA_JANELA = "verificacoes"
ARQUIVO_DO_AMBIENTE = "ambiente.json"
VARIAVEIS_QUE_A_REEXECUCAO_RECEBE = ("PROJETO", "ISSUE", "ASSUNTO")
LINHAS_DO_FIM = 12

VEREDITO_SEGUE = "segue"
VEREDITO_PARA = "para"
VEREDITO_PERGUNTA = "pergunta"
ORIGEM_DO_MOTOR = "encadeador"
BANDEIRA_DE_TESTE = "--testar"
BANDEIRA_DE_PROMOCAO = "--promover"
TEMPO_DA_VERIFICACAO = 900
TEMPO_DA_CAIXA = 120

TIPO_DEFEITO = "defeito"
TIPO_MELHORIA = "melhoria"
ACHADO_PROVA_NAO_REPRODUZ = "prova-que-nao-reproduz"
ACHADO_CICLO_REPETIDO = "etapa-que-repete-ciclo"
ACHADO_EVIDENCIA_SINTETICA = "evidencia-escrita-pelo-motor"
ACHADO_SEGUIU_SEM_PROVA = "etapa-que-segue-sem-prova"
ACHADO_EVIDENCIA_ILEGIVEL = "evidencia-que-nao-abre"
ACHADO_PROVA_SUPERADA = "prova-superada-pelo-mundo"

TITULO_PROVADO = "PROVADO — o que a execução deixou no disco"
TITULO_ILEGIVEL = "ILEGÍVEL — não auditado, não é caixa vazia"
TITULO_REEXECUCAO = "RE-EXECUÇÃO — a prova ainda reproduz?"
TITULO_SUPOSTO = "SUPOSTO — leitura, não fato"
LINHA_DA_ETAPA = "  {:>3} {:<26} {:<9} ciclo {}/{}  {}"
LINHA_DO_TOTAL = "  {:<30} {}"
LINHA_SIMPLES = "  {}"
LINHA_ILEGIVEL = "  {}: {}"
SEM_EVIDENCIA = "Nenhuma evidência em {} — nada a auditar."
TUDO_ILEGIVEL = ("Nenhuma evidência legível em {} — {} arquivo(s) que não "
                 "abrem, e isso é não auditado, não é caixa vazia:")
SEM_FORMA_DE_EVIDENCIA = "JSON válido sem forma de evidência: falta a etapa"
PASTA_INEXISTENTE = "Pasta que não existe: {}"
CABECALHO = ("\nAUDITORIA DO TRABALHO {} — {} etapa(s) em {} arquivo(s), "
             "{} ilegível(is)")

SUPOSTO_PAROU_EM = ("a execução parou em {!r}: é a última etapa com veredito "
                    "{} e nada depois dela ficou registrado")
SUPOSTO_PERGUNTOU = "a execução devolveu a decisão em {!r} e ficou esperando"
SUPOSTO_REPETIU = ("{} etapa(s) gastaram mais de um ciclo — {}. Etapa que "
                   "repete é etapa cujo critério não estava claro na primeira "
                   "passada")
SUPOSTO_SINTETICA = ("{} evidência(s) foram escritas pelo motor, não pela "
                     "etapa ({}). Isso é o motor dando nome a um estado que a "
                     "etapa não conseguiu declarar")
SUPOSTO_ILEGIVEL = ("{} arquivo(s) de evidência não abriram — {}. O que está "
                    "ali ficou fora de toda contagem acima: é não auditado, "
                    "não é caixa vazia")
SUPOSTO_SEM_PROVA = ("{} etapa(s) seguiram sem nenhum item provado — {}. "
                     "Veredito que segue sem prova é a regra 2 sendo "
                     "contornada")
SUPOSTO_LIMPO = "nada a apontar: toda etapa seguiu, com prova e num ciclo só"
SUPOSTO_PROVA_NAO_REPRODUZ = ("prova que não reproduz mais é o achado "
                              "mais forte desta auditoria: o comando e a saída "
                              "estavam declarados e agora dão outra coisa. Ou o "
                              "mundo mudou, ou a prova foi redigida em vez de colada")
SUPOSTO_PROVA_SUPERADA = ("prova superada pelo mundo: {} prova(s) não "
                          "reproduzem mais, e o disco mostra que reproduziram "
                          "na hora da etapa — {}. O mundo andou depois da "
                          "etapa; aqui não cabe falar em prova forjada")
SUPERADA_UMA = "{} ({})"
MOTIVO_DA_JANELA = "verificada na janela em {}"
MOTIVO_DO_CICLO = "o ciclo {} da mesma etapa seguiu depois"
VERIFICADOR_AUSENTE = ("verificador não encontrado em {} — a re-execução não "
                       "rodou, e isso é não medido, não é aprovação")
VERIFICADOR_OK = "o verificador re-executou as provas e não acusou divergência"
VERIFICADOR_ACUSOU = "o verificador acusou (saída {}):"

TITULO_PROMOVIDO = "PROMOVIDO — o achado que virou linha na caixa"
ASSUNTO_DO_ACHADO = "{trabalho}: {texto}"
NADA_A_PROMOVER = ("nada: dos supostos acima, nenhum é dos que o auditor sabe "
                   "nomear — os outros ficam só impressos")
PROMOCAO_DESLIGADA = ("desligada: o achado fica só impresso. Ligue com {} — "
                      "quem chama o auditor decide se o achado vira linha")
CAIXA_AUSENTE = ("instrumento da caixa não encontrado em {} — nada foi "
                 "promovido, e isso é não promovido, não é caixa vazia")
FALHOU_AO_PROMOVER = "não promovi {}: {}"


def evidencias_da_pasta(pasta: Path) -> tuple:
    achadas, ilegiveis = [], []
    for caminho in sorted(pasta.glob(GLOB_DE_EVIDENCIA)):
        if not NOME_DA_EVIDENCIA.match(caminho.name):
            continue
        try:
            dado = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            ilegiveis.append((caminho, str(erro)))
            continue
        if isinstance(dado, dict) and dado.get("etapa"):
            achadas.append((caminho, dado))
        else:
            ilegiveis.append((caminho, SEM_FORMA_DE_EVIDENCIA))
    return achadas, ilegiveis


def ordem_da_evidencia(caminho: Path) -> str:
    achado = NOME_DA_EVIDENCIA.match(caminho.name)
    return achado.group(1) if achado else "?"


def contar(evidencias: list, ilegiveis: list = ()) -> dict:
    ciclos = [e for _, e in evidencias if (e.get("ciclo") or {}).get("i", 1) > 1]
    sinteticas = [e for _, e in evidencias
                  if e.get("origem") == ORIGEM_DO_MOTOR]
    sem_prova = [e for _, e in evidencias
                 if e.get("veredito") == VEREDITO_SEGUE and not e.get("provado")]
    return {
        "etapas": len({e.get("etapa") for _, e in evidencias}),
        "arquivos": len(evidencias),
        "segue": sum(1 for _, e in evidencias
                     if e.get("veredito") == VEREDITO_SEGUE),
        "para": sum(1 for _, e in evidencias
                    if e.get("veredito") == VEREDITO_PARA),
        "pergunta": sum(1 for _, e in evidencias
                        if e.get("veredito") == VEREDITO_PERGUNTA),
        "provas": sum(len(e.get("provado") or []) for _, e in evidencias),
        "repetidas": [e["etapa"] for e in ciclos],
        "sinteticas": [e["etapa"] for e in sinteticas],
        "sem_prova": [e["etapa"] for e in sem_prova],
        "ilegiveis": [(str(caminho), erro) for caminho, erro in ilegiveis],
    }


def linhas_da_acusacao(saida: str) -> list:
    return [linha for linha in (saida or "").splitlines()
            if linha.startswith(PREFIXO_DA_ACUSACAO)]


def acusadas(saida: str) -> list:
    nomes = []
    for linha in linhas_da_acusacao(saida):
        rotulada = ACUSACAO_ROTULADA.match(linha)
        if rotulada and rotulada.group(1) not in nomes:
            nomes.append(rotulada.group(1))
    return nomes


def registro_da_janela(pasta: Path, nome: str) -> dict:
    try:
        dado = json.loads((pasta / PASTA_DA_JANELA / nome)
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dado if isinstance(dado, dict) else {}


def ambiente_da_execucao(pasta: Path) -> dict:
    try:
        dado = json.loads((pasta / ARQUIVO_DO_AMBIENTE)
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(os.environ)
    gravadas = dado.get("variaveis") if isinstance(dado, dict) else None
    if not isinstance(gravadas, dict):
        return dict(os.environ)
    return dict(os.environ, **{
        nome: str(gravadas[nome])
        for nome in VARIAVEIS_QUE_A_REEXECUCAO_RECEBE
        if isinstance(gravadas.get(nome), (str, int))})


def _ciclo_que_seguiu_depois(evidencias: list, nome: str) -> str:
    acusada = NOME_DA_EVIDENCIA.match(nome)
    if not acusada:
        return ""
    for caminho, dado in evidencias:
        outra = NOME_DA_EVIDENCIA.match(caminho.name)
        if (outra and outra.group(2) == acusada.group(2)
                and int(outra.group(3)) > int(acusada.group(3))
                and dado.get("veredito") == VEREDITO_SEGUE):
            return outra.group(3)
    return ""


def superacao(pasta: Path, evidencias: list, nome: str) -> str:
    registro = registro_da_janela(pasta, nome)
    if isinstance(registro.get("exit"), int):
        return (MOTIVO_DA_JANELA.format(registro.get("quando") or "?")
                if registro["exit"] == 0 else "")
    ciclo = _ciclo_que_seguiu_depois(evidencias, nome)
    return MOTIVO_DO_CICLO.format(ciclo) if ciclo else ""


def julgar_a_janela(pasta: Path, evidencias: list, saida: str) -> dict:
    superadas, fortes = [], []
    for nome in acusadas(saida):
        motivo = superacao(pasta, evidencias, nome)
        if motivo:
            superadas.append(SUPERADA_UMA.format(nome, motivo))
        else:
            fortes.append(nome)
    return {"superadas": superadas, "fortes": fortes}


def _lido(texto: str, identidade: str = "", tipo: str = "") -> dict:
    return {"texto": texto, "id": identidade, "tipo": tipo}


def lidos_da_execucao(evidencias: list, conta: dict,
                      reproduz: bool = True, janela: dict = None) -> list:
    lidos = []
    superadas = (janela or {}).get("superadas") or []
    fortes = (janela or {}).get("fortes") or []
    if not reproduz and (fortes or not superadas):
        lidos.append(_lido(SUPOSTO_PROVA_NAO_REPRODUZ,
                           ACHADO_PROVA_NAO_REPRODUZ, TIPO_DEFEITO))
    if not reproduz and superadas:
        lidos.append(_lido(
            SUPOSTO_PROVA_SUPERADA.format(len(superadas),
                                          ", ".join(superadas)),
            ACHADO_PROVA_SUPERADA, TIPO_MELHORIA))
    if conta["ilegiveis"]:
        lidos.append(_lido(SUPOSTO_ILEGIVEL.format(
            len(conta["ilegiveis"]),
            ", ".join(Path(caminho).name
                      for caminho, _ in conta["ilegiveis"])),
            ACHADO_EVIDENCIA_ILEGIVEL, TIPO_DEFEITO))
    ultima = evidencias[-1][1] if evidencias else {}
    if ultima.get("veredito") == VEREDITO_PARA:
        lidos.append(_lido(SUPOSTO_PAROU_EM.format(ultima.get("etapa"),
                                                   VEREDITO_PARA)))
    if ultima.get("veredito") == VEREDITO_PERGUNTA:
        lidos.append(_lido(SUPOSTO_PERGUNTOU.format(ultima.get("etapa"))))
    if conta["repetidas"]:
        lidos.append(_lido(SUPOSTO_REPETIU.format(
            len(conta["repetidas"]), ", ".join(conta["repetidas"])),
            ACHADO_CICLO_REPETIDO, TIPO_MELHORIA))
    if conta["sinteticas"]:
        lidos.append(_lido(SUPOSTO_SINTETICA.format(
            len(conta["sinteticas"]), ", ".join(conta["sinteticas"])),
            ACHADO_EVIDENCIA_SINTETICA, TIPO_DEFEITO))
    if conta["sem_prova"]:
        lidos.append(_lido(SUPOSTO_SEM_PROVA.format(
            len(conta["sem_prova"]), ", ".join(conta["sem_prova"])),
            ACHADO_SEGUIU_SEM_PROVA, TIPO_DEFEITO))
    return lidos or [_lido(SUPOSTO_LIMPO)]


def supostos(evidencias: list, conta: dict, reproduz: bool = True,
             janela: dict = None) -> list:
    return [um["texto"]
            for um in lidos_da_execucao(evidencias, conta, reproduz, janela)]


def os_que_sabe_nomear(lidos: list) -> list:
    return [um for um in lidos if um["id"]]


def promover(trabalho: str, lidos: list, cwd: str = "") -> tuple:
    if not CAIXA.is_file():
        return False, [CAIXA_AUSENTE.format(CAIXA)]
    recados, inteiro = [], True
    for um in lidos:
        comando = [sys.executable, str(CAIXA), um["tipo"], "--id", um["id"],
                   "--assunto", ASSUNTO_DO_ACHADO.format(trabalho=trabalho,
                                                         texto=um["texto"])]
        if cwd:
            comando += ["--cwd", cwd]
        try:
            feito = subprocess.run(comando, capture_output=True, text=True,
                                   timeout=TEMPO_DA_CAIXA)
        except (OSError, subprocess.SubprocessError) as erro:
            recados.append(FALHOU_AO_PROMOVER.format(um["id"], erro))
            inteiro = False
            continue
        if feito.returncode != 0:
            inteiro = False
        recados.append((feito.stdout + feito.stderr).strip()
                       or FALHOU_AO_PROMOVER.format(um["id"],
                                                    feito.returncode))
    return inteiro, recados


def reexecutar(pasta: Path, cwd: str) -> tuple:
    if not VERIFICADOR.is_file():
        return None, VERIFICADOR_AUSENTE.format(VERIFICADOR)
    comando = [sys.executable, str(VERIFICADOR), "trabalho", str(pasta)]
    if cwd:
        comando += ["--cwd", cwd]
    try:
        pronto = subprocess.run(comando, capture_output=True, text=True,
                                env=ambiente_da_execucao(pasta),
                                timeout=TEMPO_DA_VERIFICACAO)
    except (OSError, subprocess.SubprocessError) as erro:
        return None, str(erro)
    return pronto.returncode, (pronto.stdout + pronto.stderr).strip()


def auditar(pasta: Path, cwd: str = "", promovendo: bool = False) -> int:
    if not pasta.is_dir():
        print(PASTA_INEXISTENTE.format(pasta))
        return 2
    evidencias, ilegiveis = evidencias_da_pasta(pasta)
    if not evidencias:
        print(TUDO_ILEGIVEL.format(pasta, len(ilegiveis)) if ilegiveis
              else SEM_EVIDENCIA.format(pasta))
        for caminho, erro in ilegiveis:
            print(LINHA_ILEGIVEL.format(caminho, erro))
        return 2

    conta = contar(evidencias, ilegiveis)
    print(CABECALHO.format(pasta.name, conta["etapas"], conta["arquivos"],
                           len(conta["ilegiveis"])))

    print(f"\n{TITULO_PROVADO}")
    for caminho, dado in evidencias:
        ciclo = dado.get("ciclo") or {}
        faltas = dado.get("faltas") or []
        print(LINHA_DA_ETAPA.format(
            ordem_da_evidencia(caminho), dado.get("etapa", "?")[:26],
            dado.get("veredito", "?"), ciclo.get("i", "?"),
            ciclo.get("teto", "?"),
            f"{len(faltas)} falta(s)" if faltas else ""))
    for rotulo, chave in (("seguiram", "segue"), ("pararam", "para"),
                          ("perguntaram", "pergunta"),
                          ("itens provados", "provas")):
        print(LINHA_DO_TOTAL.format(rotulo, conta[chave]))
    print(LINHA_DO_TOTAL.format("ilegíveis", len(conta["ilegiveis"])))

    if conta["ilegiveis"]:
        print(f"\n{TITULO_ILEGIVEL}")
        for caminho, erro in conta["ilegiveis"]:
            print(LINHA_ILEGIVEL.format(caminho, erro))

    print(f"\n{TITULO_REEXECUCAO}")
    codigo, saida = reexecutar(pasta, cwd)
    janela = {}
    if codigo is None:
        print(LINHA_SIMPLES.format(saida))
    elif codigo == 0:
        print(LINHA_SIMPLES.format(VERIFICADOR_OK))
    else:
        janela = julgar_a_janela(pasta, evidencias, saida)
        print(LINHA_SIMPLES.format(VERIFICADOR_ACUSOU.format(codigo)))
        for linha in (linhas_da_acusacao(saida)
                      or saida.split("\n")[-LINHAS_DO_FIM:]):
            print(LINHA_SIMPLES.format(linha))

    lidos = lidos_da_execucao(evidencias, conta, codigo in (0, None), janela)
    print(f"\n{TITULO_SUPOSTO}")
    for lido in lidos:
        print(LINHA_SIMPLES.format(lido["texto"]))

    print(f"\n{TITULO_PROMOVIDO}")
    nomeados = os_que_sabe_nomear(lidos)
    promoveu = True
    if not promovendo:
        print(LINHA_SIMPLES.format(
            PROMOCAO_DESLIGADA.format(BANDEIRA_DE_PROMOCAO)))
    elif not nomeados:
        print(LINHA_SIMPLES.format(NADA_A_PROMOVER))
    else:
        promoveu, recados = promover(pasta.name, nomeados, cwd)
        for recado in recados:
            print(LINHA_SIMPLES.format(recado))

    if not promoveu:
        return 2
    houve_falha = (conta["para"] > 0 or bool(conta["ilegiveis"])
                   or (codigo not in (0, None)))
    return 1 if houve_falha else 0


def _evidencia(etapa, veredito=VEREDITO_SEGUE, ciclo=1, provado=None,
               origem=None, faltas=None) -> dict:
    dado = {"etapa": etapa, "trabalho": "t", "quando": "2000-01-01T00:00:00Z",
            "veredito": veredito, "provado": provado or [], "suposto": [],
            "faltas": faltas or [], "ciclo": {"i": ciclo, "teto": 3}}
    if origem:
        dado["origem"] = origem
    return dado


def _escrever(pasta: Path, ordem, etapa, **troca) -> None:
    ciclo = troca.get("ciclo", 1)
    alvo = pasta / f"{ordem:02d}-{etapa}-c{ciclo}.json"
    alvo.write_text(json.dumps(_evidencia(etapa, **troca), ensure_ascii=False),
                    encoding="utf-8")


FALSA_CAIXA = """import os
import sys
from pathlib import Path

with Path(os.environ["AUDITOR_TESTE_LOG"]).open("a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]).replace(chr(10), " ") + chr(10))
sys.exit(2 if os.environ.get("AUDITOR_TESTE_RECUSA") else 0)
"""

FALSO_VERIFICADOR = """import os
import sys

sys.stdout.write(os.environ["AUDITOR_TESTE_SAIDA"])
sys.exit(4)
"""

VERIFICADOR_QUE_RELATA_O_AMBIENTE = """import os
import sys

for nome in ("PROJETO", "GH_TOKEN"):
    sys.stdout.write(nome + "=" + os.environ.get(nome, "<ausente>") + chr(10))
sys.exit(4)
"""
AMBIENTE_COM_SEGREDO_INFILTRADO = {
    "variaveis": {"PROJETO": "alvo-gravado", "ISSUE": "68",
                  "ASSUNTO": "forja", "GH_TOKEN": "ghp_contrabando"}}
ALVO_DO_SHELL = "alvo-do-shell-que-nao-manda"
QUANDO_DA_JANELA = "2000-01-02T00:00:00Z"


def testar() -> int:
    import contextlib
    import io
    import os
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, condicao):
        rodados.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    def falado(*argumentos, **troca):
        conversa = io.StringIO()
        with contextlib.redirect_stdout(conversa):
            codigo = auditar(*argumentos, **troca)
        return codigo, conversa.getvalue()

    with tempfile.TemporaryDirectory(prefix="auditor-teste-") as pasta:
        vazia = Path(pasta) / "vazia"
        vazia.mkdir()
        caso("pasta sem evidência não vira auditoria",
             auditar(vazia) == 2)
        caso("pasta que não existe é recusada",
             auditar(Path(pasta) / "nao-existe") == 2)

        boa = Path(pasta) / "boa"
        boa.mkdir()
        _escrever(boa, 1, "abrir", provado=[{"afirmacao": "a", "comando": "true",
                                             "saida": ""}])
        _escrever(boa, 2, "fechar", provado=[{"afirmacao": "b", "comando": "true",
                                              "saida": ""}])
        evidencias, _ = evidencias_da_pasta(boa)
        conta = contar(evidencias)
        caso("conta as etapas e os itens provados",
             conta["etapas"] == 2 and conta["provas"] == 2)
        caso("execução limpa não gera suposto inventado",
             supostos(evidencias, conta) == [SUPOSTO_LIMPO])

        suja = Path(pasta) / "suja"
        suja.mkdir()
        _escrever(suja, 1, "tentar", ciclo=2,
                  provado=[{"afirmacao": "a", "comando": "true", "saida": ""}])
        _escrever(suja, 2, "seguir-sem-prova")
        _escrever(suja, 3, "morrer", veredito=VEREDITO_PARA,
                  origem=ORIGEM_DO_MOTOR, faltas=["estourou"])
        evidencias, _ = evidencias_da_pasta(suja)
        conta = contar(evidencias)
        lidos = " ".join(supostos(evidencias, conta))
        caso("aponta a etapa que repetiu ciclo", "tentar" in lidos)
        caso("aponta a evidência escrita pelo motor", "morrer" in lidos)
        caso("aponta quem seguiu sem prova nenhuma",
             "seguir-sem-prova" in lidos)
        caso("diz onde a execução parou", SUPOSTO_PAROU_EM.split("{")[0] in lidos)
        caso("execução que parou devolve saída diferente de zero",
             auditar(suja) == 1)

        perguntou = Path(pasta) / "perguntou"
        perguntou.mkdir()
        _escrever(perguntou, 1, "decidir", veredito=VEREDITO_PERGUNTA)
        evidencias, _ = evidencias_da_pasta(perguntou)
        caso("pergunta não é falha: a execução devolveu a decisão",
             SUPOSTO_PERGUNTOU.split("{")[0]
             in " ".join(supostos(evidencias, contar(evidencias))))

        caso("a ordem sai do nome do arquivo",
             ordem_da_evidencia(Path("07-etapa-c1.json")) == "07")
        caso("nome fora do padrão não derruba a leitura",
             ordem_da_evidencia(Path("solto.json")) == "?")

        com_estado = Path(pasta) / "com-estado"
        com_estado.mkdir()
        _escrever(com_estado, 1, "unica",
                  provado=[{"afirmacao": "a", "comando": "true",
                            "saida": ""}])
        (com_estado / "estado.json").write_text(
            json.dumps({"etapa": "unica", "trabalho": "t"}),
            encoding="utf-8")
        caso("o estado do motor não é lido como evidência",
             len(evidencias_da_pasta(com_estado)[0]) == 1)
        corrompida = Path(pasta) / "corrompida"
        corrompida.mkdir()
        _escrever(corrompida, 1, "legivel",
                  provado=[{"afirmacao": "a", "comando": "true",
                            "saida": ""}])
        (corrompida / "02-bytes-c1.json").write_bytes(b"\xff\xfe nao e utf-8")
        (corrompida / "03-json-partido-c1.json").write_text(
            '{"etapa": "meia', encoding="utf-8")
        (corrompida / "04-lista-c1.json").write_text(
            json.dumps(["isto não é evidência"]), encoding="utf-8")
        (corrompida / "05-sem-etapa-c1.json").write_text(
            json.dumps({"veredito": VEREDITO_SEGUE}), encoding="utf-8")
        legiveis, nao_abriram = evidencias_da_pasta(corrompida)
        nomeados_ilegiveis = [c.name for c, _ in nao_abriram]
        caso("bytes inválidos não somem: viram ilegível com caminho e erro",
             len(legiveis) == 1
             and all(erro for _, erro in nao_abriram)
             and "02-bytes-c1.json" in nomeados_ilegiveis)
        caso("JSON partido no meio não some: vira ilegível nomeado",
             "03-json-partido-c1.json" in nomeados_ilegiveis)
        caso("JSON válido sem forma de evidência não é descarte calado",
             [c.name for c, erro in nao_abriram
              if erro == SEM_FORMA_DE_EVIDENCIA]
             == ["04-lista-c1.json", "05-sem-etapa-c1.json"])
        conta_ilegivel = contar(legiveis, nao_abriram)
        caso("o ilegível entra na contagem em vez de sumir dela",
             len(conta_ilegivel["ilegiveis"]) == 4
             and conta_ilegivel["arquivos"] == 1)
        dito_suposto = " ".join(supostos(legiveis, conta_ilegivel))
        caso("o ilegível vira suposto que nomeia cada arquivo",
             sum(nome in dito_suposto for nome in nomeados_ilegiveis) == 4)

        global VERIFICADOR
        guardado = VERIFICADOR
        VERIFICADOR = Path(pasta) / "sem-verificador.py"
        try:
            codigo, dito = falado(corrompida)
            caso("o relatório nomeia cada ilegível, um por linha",
                 sum(dito.count(LINHA_ILEGIVEL.format(
                     corrompida / nome, "").rstrip())
                     for nome in nomeados_ilegiveis) == 4)
            caso("o cabeçalho conta os ilegíveis junto com os arquivos",
                 CABECALHO.format(corrompida.name, 1, 1, 4) in dito)
            caso("evidência ilegível sozinha já faz o auditor sair não zero",
                 codigo == 1)

            toda_ilegivel = Path(pasta) / "toda-ilegivel"
            toda_ilegivel.mkdir()
            (toda_ilegivel / "01-unica-c1.json").write_bytes(b"\xff nao abre")
            codigo_ilegivel, dito_ilegivel = falado(toda_ilegivel)
            codigo_vazia, dito_vazia = falado(vazia)
            caso("pasta toda ilegível não se confunde com pasta vazia",
                 dito_ilegivel != dito_vazia
                 and SEM_EVIDENCIA.split("{")[0] in dito_vazia
                 and SEM_EVIDENCIA.split("{")[0] not in dito_ilegivel)
            caso("pasta toda ilegível nomeia o arquivo e sai diferente de 0",
                 codigo_ilegivel != 0 and codigo_vazia != 0
                 and "01-unica-c1.json" in dito_ilegivel)
        finally:
            VERIFICADOR = guardado

        limpa, _ = evidencias_da_pasta(boa)
        caso("prova que não reproduz vira o suposto mais forte",
             supostos(limpa, contar(limpa), reproduz=False)[0]
             == SUPOSTO_PROVA_NAO_REPRODUZ)
        caso("e quando reproduz, ele não aparece",
             SUPOSTO_PROVA_NAO_REPRODUZ
             not in supostos(limpa, contar(limpa)))

        janela = Path(pasta) / "janela"
        janela.mkdir()
        uma_prova = [{"afirmacao": "a", "comando": "true", "saida": ""}]
        _escrever(janela, 1, "superada", provado=uma_prova)
        _escrever(janela, 2, "sem-registro", provado=uma_prova)
        _escrever(janela, 3, "acusou-na-janela", provado=uma_prova)
        _escrever(janela, 4, "repetida", ciclo=1, provado=uma_prova)
        _escrever(janela, 4, "repetida", ciclo=2, provado=uma_prova)
        (janela / PASTA_DA_JANELA).mkdir()
        for nome, saiu in (("01-superada-c1.json", 0),
                           ("03-acusou-na-janela-c1.json", 4)):
            (janela / PASTA_DA_JANELA / nome).write_text(
                json.dumps({"alvo": nome, "quando": QUANDO_DA_JANELA,
                            "exit": saiu}), encoding="utf-8")
        acusou = "\n".join(
            f"ACUSA [{nome}] saída diverge em 'git log': o mundo andou"
            for nome in ("01-superada-c1.json", "02-sem-registro-c1.json",
                         "03-acusou-na-janela-c1.json",
                         "04-repetida-c1.json")) + "\n\n4 acusações."
        de_janela, _ = evidencias_da_pasta(janela)
        julgado = julgar_a_janela(janela, de_janela, acusou)
        caso("a acusação diz de qual evidência ela é, sem repetir nome",
             acusadas(acusou + "\n" + acusou)
             == ["01-superada-c1.json", "02-sem-registro-c1.json",
                 "03-acusou-na-janela-c1.json", "04-repetida-c1.json"])
        caso("registro de janela com exit 0 é prova superada, e cita o quando",
             SUPERADA_UMA.format("01-superada-c1.json",
                                 MOTIVO_DA_JANELA.format(QUANDO_DA_JANELA))
             in julgado["superadas"])
        caso("ciclo mais novo da mesma etapa que seguiu também é superação",
             SUPERADA_UMA.format("04-repetida-c1.json",
                                 MOTIVO_DO_CICLO.format("2"))
             in julgado["superadas"])
        caso("registro de janela ausente mantém o achado forte",
             "02-sem-registro-c1.json" in julgado["fortes"])
        caso("registro de janela que já acusou na hora mantém o achado forte",
             "03-acusou-na-janela-c1.json" in julgado["fortes"])
        dito_janela = supostos(de_janela, contar(de_janela), reproduz=False,
                               janela=julgado)
        caso("prova superada vira achado próprio, ao lado do achado forte",
             any(SUPOSTO_PROVA_SUPERADA.split("{")[0] in um
                 for um in dito_janela)
             and SUPOSTO_PROVA_NAO_REPRODUZ in dito_janela)
        so_superadas = julgar_a_janela(
            janela, de_janela, "ACUSA [01-superada-c1.json] saída diverge")
        caso("acusação toda superada tira a frase de forja do relatório",
             SUPOSTO_PROVA_NAO_REPRODUZ
             not in supostos(de_janela, contar(de_janela), reproduz=False,
                             janela=so_superadas))
        caso("prova superada pelo mundo é achado de melhoria, nomeado",
             {um["id"]: um["tipo"] for um in os_que_sabe_nomear(
                 lidos_da_execucao(de_janela, contar(de_janela),
                                   reproduz=False, janela=julgado))}
             .get(ACHADO_PROVA_SUPERADA) == TIPO_MELHORIA)

        falso_verificador = Path(pasta) / "falso_verificador.py"
        falso_verificador.write_text(FALSO_VERIFICADOR, encoding="utf-8")
        longe_do_fim = ("ACUSA [01-superada-c1.json] saída diverge em "
                        "'git log': o mundo andou")
        os.environ["AUDITOR_TESTE_SAIDA"] = "\n".join(
            [longe_do_fim] + [f"linha de enchimento {n}" for n in range(20)])
        VERIFICADOR = falso_verificador
        try:
            _, relato = falado(janela)
            caso("acusação longe do fim não é cortada do relatório",
                 longe_do_fim in relato)
            caso("e o relatório fecha a superação citando o quando da janela",
                 SUPOSTO_PROVA_SUPERADA.split("{")[0] in relato
                 and QUANDO_DA_JANELA in relato)
        finally:
            VERIFICADOR = guardado
            os.environ.pop("AUDITOR_TESTE_SAIDA", None)

        com_ambiente = Path(pasta) / "com-ambiente"
        com_ambiente.mkdir()
        _escrever(com_ambiente, 1, "abrir",
                  provado=[{"afirmacao": "a", "comando": "true", "saida": ""}])
        gravado = com_ambiente / ARQUIVO_DO_AMBIENTE
        gravado.write_text(json.dumps(AMBIENTE_COM_SEGREDO_INFILTRADO),
                           encoding="utf-8")
        relator = Path(pasta) / "relator_do_ambiente.py"
        relator.write_text(VERIFICADOR_QUE_RELATA_O_AMBIENTE,
                           encoding="utf-8")
        chamariz = os.environ.get("PROJETO")
        token_de_quem_audita = os.environ.pop("GH_TOKEN", None)
        os.environ["PROJETO"] = ALVO_DO_SHELL
        VERIFICADOR = relator
        try:
            _, com_gravado = falado(com_ambiente)
            caso("a re-execução recebe o PROJETO que a execução gravou, "
                 "não o do shell que audita",
                 "PROJETO=alvo-gravado" in com_gravado)
            caso("ambiente gravado só entrega o que a lista permite: segredo "
                 "que apareça no arquivo não chega à re-execução",
                 "GH_TOKEN=<ausente>" in com_gravado)
            gravado.unlink()
            _, sem_gravado = falado(com_ambiente)
            caso("evidência sem ambiente gravado re-executa como antes",
                 f"PROJETO={ALVO_DO_SHELL}" in sem_gravado)
        finally:
            VERIFICADOR = guardado
            os.environ.pop("PROJETO", None)
            if chamariz is not None:
                os.environ["PROJETO"] = chamariz
            if token_de_quem_audita is not None:
                os.environ["GH_TOKEN"] = token_de_quem_audita

        falsa_caixa = Path(pasta) / "falsa_caixa.py"
        registro = Path(pasta) / "registro.txt"
        falsa_caixa.write_text(FALSA_CAIXA, encoding="utf-8")
        os.environ["AUDITOR_TESTE_LOG"] = str(registro)
        global CAIXA
        guardada = CAIXA
        CAIXA = falsa_caixa
        try:
            evidencias, _ = evidencias_da_pasta(suja)
            conta = contar(evidencias)
            nomeados = os_que_sabe_nomear(
                lidos_da_execucao(evidencias, conta, reproduz=False))
            porid = {um["id"]: um["tipo"] for um in nomeados}
            caso("prova que não reproduz é achado de defeito, nomeado",
                 porid.get(ACHADO_PROVA_NAO_REPRODUZ) == TIPO_DEFEITO)
            caso("etapa que repetiu ciclo é achado de melhoria",
                 porid.get(ACHADO_CICLO_REPETIDO) == TIPO_MELHORIA)
            caso("evidência escrita pelo motor é achado de defeito",
                 porid.get(ACHADO_EVIDENCIA_SINTETICA) == TIPO_DEFEITO)
            caso("etapa que seguiu sem prova é achado de defeito",
                 porid.get(ACHADO_SEGUIU_SEM_PROVA) == TIPO_DEFEITO)
            nomeados_do_ilegivel = os_que_sabe_nomear(lidos_da_execucao(
                legiveis, contar(legiveis, nao_abriram)))
            caso("evidência que não abre é achado de defeito, nomeado",
                 {um["id"]: um["tipo"] for um in nomeados_do_ilegivel}
                 .get(ACHADO_EVIDENCIA_ILEGIVEL) == TIPO_DEFEITO)
            caso("execução que parou não vira achado: fica só impressa",
                 len(nomeados) == 4
                 and SUPOSTO_PAROU_EM.split("{")[0]
                 in " ".join(supostos(evidencias, conta, reproduz=False)))

            limpa, _ = evidencias_da_pasta(boa)
            caso("execução limpa não promove nada",
                 os_que_sabe_nomear(
                     lidos_da_execucao(limpa, contar(limpa))) == [])

            de_outro, _ = evidencias_da_pasta(perguntou)
            caso("execução que perguntou também não vira achado",
                 os_que_sabe_nomear(
                     lidos_da_execucao(de_outro, contar(de_outro))) == [])

            registro.write_text("", encoding="utf-8")
            caso("sem --promover, o auditor não chama a caixa",
                 auditar(suja) == 1
                 and registro.read_text(encoding="utf-8") == "")

            registro.write_text("", encoding="utf-8")
            auditar(suja, promovendo=True)
            chamadas = registro.read_text(encoding="utf-8").splitlines()
            caso("com --promover, chama a caixa uma vez por achado nomeado",
                 len(chamadas) == len(os_que_sabe_nomear(
                     lidos_da_execucao(evidencias, conta, reproduz=False))))
            caso("e o assunto promovido diz de qual trabalho veio",
                 all("suja" in uma for uma in chamadas))
            caso("a identidade não carrega o trabalho: é estável entre eles",
                 sum(1 for uma in chamadas
                     if "--id " + ACHADO_PROVA_NAO_REPRODUZ in uma) == 1)

            registro.write_text("", encoding="utf-8")
            os.environ["AUDITOR_TESTE_RECUSA"] = "1"
            caso("caixa que recusa faz o auditor sair diferente de zero",
                 auditar(suja, promovendo=True) == 2)
            os.environ.pop("AUDITOR_TESTE_RECUSA")

            CAIXA = Path(pasta) / "nao-existe.py"
            caso("caixa ausente é não promovido, não é caixa vazia",
                 auditar(suja, promovendo=True) == 2)
        finally:
            CAIXA = guardada
            os.environ.pop("AUDITOR_TESTE_LOG", None)

    total = len(rodados)
    if falhas:
        for falha in falhas:
            print(f"  [{falha}]")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — leitura da execução, contagem e suposto")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("pasta", help="a pasta de evidências de um trabalho")
    ap.add_argument("--cwd", default="",
                    help="onde re-executar as provas (padrão: aqui)")
    ap.add_argument(BANDEIRA_DE_PROMOCAO, action="store_true",
                    dest="promovendo",
                    help="põe na caixa o achado que o auditor sabe nomear")
    a = ap.parse_args()
    return auditar(Path(a.pasta), a.cwd, a.promovendo)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
