import argparse
import json
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
GLOB_DE_EVIDENCIA = "*.json"
NOME_DA_EVIDENCIA = re.compile(r"^(\d+)-(.+)-c(\d+)\.json$")

VEREDITO_SEGUE = "segue"
VEREDITO_PARA = "para"
VEREDITO_PERGUNTA = "pergunta"
ORIGEM_DO_MOTOR = "encadeador"
BANDEIRA_DE_TESTE = "--testar"
TEMPO_DA_VERIFICACAO = 900

TITULO_PROVADO = "PROVADO — o que a execução deixou no disco"
TITULO_REEXECUCAO = "RE-EXECUÇÃO — a prova ainda reproduz?"
TITULO_SUPOSTO = "SUPOSTO — leitura, não fato"
LINHA_DA_ETAPA = "  {:>3} {:<26} {:<9} ciclo {}/{}  {}"
LINHA_DO_TOTAL = "  {:<30} {}"
LINHA_SIMPLES = "  {}"
SEM_EVIDENCIA = "Nenhuma evidência em {} — nada a auditar."
PASTA_INEXISTENTE = "Pasta que não existe: {}"
CABECALHO = "\nAUDITORIA DO TRABALHO {} — {} etapa(s) em {} arquivo(s)"

SUPOSTO_PAROU_EM = ("a execução parou em {!r}: é a última etapa com veredito "
                    "{} e nada depois dela ficou registrado")
SUPOSTO_PERGUNTOU = "a execução devolveu a decisão em {!r} e ficou esperando"
SUPOSTO_REPETIU = ("{} etapa(s) gastaram mais de um ciclo — {}. Etapa que "
                   "repete é etapa cujo critério não estava claro na primeira "
                   "passada")
SUPOSTO_SINTETICA = ("{} evidência(s) foram escritas pelo motor, não pela "
                     "etapa ({}). Isso é o motor dando nome a um estado que a "
                     "etapa não conseguiu declarar")
SUPOSTO_SEM_PROVA = ("{} etapa(s) seguiram sem nenhum item provado — {}. "
                     "Veredito que segue sem prova é a regra 2 sendo "
                     "contornada")
SUPOSTO_LIMPO = "nada a apontar: toda etapa seguiu, com prova e num ciclo só"
SUPOSTO_PROVA_NAO_REPRODUZ = ("prova que não reproduz mais é o achado "
                              "mais forte desta auditoria: o comando e a saída "
                              "estavam declarados e agora dão outra coisa. Ou o "
                              "mundo mudou, ou a prova foi redigida em vez de colada")
VERIFICADOR_AUSENTE = ("verificador não encontrado em {} — a re-execução não "
                       "rodou, e isso é não medido, não é aprovação")
VERIFICADOR_OK = "o verificador re-executou as provas e não acusou divergência"
VERIFICADOR_ACUSOU = "o verificador acusou (saída {}):"


def evidencias_da_pasta(pasta: Path) -> list:
    achadas = []
    for caminho in sorted(pasta.glob(GLOB_DE_EVIDENCIA)):
        if not NOME_DA_EVIDENCIA.match(caminho.name):
            continue
        try:
            dado = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(dado, dict) and dado.get("etapa"):
            achadas.append((caminho, dado))
    return achadas


def ordem_da_evidencia(caminho: Path) -> str:
    achado = NOME_DA_EVIDENCIA.match(caminho.name)
    return achado.group(1) if achado else "?"


def contar(evidencias: list) -> dict:
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
    }


def supostos(evidencias: list, conta: dict, reproduz: bool = True) -> list:
    lidos = []
    if not reproduz:
        lidos.append(SUPOSTO_PROVA_NAO_REPRODUZ)
    ultima = evidencias[-1][1] if evidencias else {}
    if ultima.get("veredito") == VEREDITO_PARA:
        lidos.append(SUPOSTO_PAROU_EM.format(ultima.get("etapa"),
                                             VEREDITO_PARA))
    if ultima.get("veredito") == VEREDITO_PERGUNTA:
        lidos.append(SUPOSTO_PERGUNTOU.format(ultima.get("etapa")))
    if conta["repetidas"]:
        lidos.append(SUPOSTO_REPETIU.format(len(conta["repetidas"]),
                                            ", ".join(conta["repetidas"])))
    if conta["sinteticas"]:
        lidos.append(SUPOSTO_SINTETICA.format(len(conta["sinteticas"]),
                                              ", ".join(conta["sinteticas"])))
    if conta["sem_prova"]:
        lidos.append(SUPOSTO_SEM_PROVA.format(len(conta["sem_prova"]),
                                              ", ".join(conta["sem_prova"])))
    return lidos or [SUPOSTO_LIMPO]


def reexecutar(pasta: Path, cwd: str) -> tuple:
    if not VERIFICADOR.is_file():
        return None, VERIFICADOR_AUSENTE.format(VERIFICADOR)
    comando = [sys.executable, str(VERIFICADOR), "trabalho", str(pasta)]
    if cwd:
        comando += ["--cwd", cwd]
    try:
        pronto = subprocess.run(comando, capture_output=True, text=True,
                                timeout=TEMPO_DA_VERIFICACAO)
    except (OSError, subprocess.SubprocessError) as erro:
        return None, str(erro)
    return pronto.returncode, (pronto.stdout + pronto.stderr).strip()


def auditar(pasta: Path, cwd: str = "") -> int:
    if not pasta.is_dir():
        print(PASTA_INEXISTENTE.format(pasta))
        return 2
    evidencias = evidencias_da_pasta(pasta)
    if not evidencias:
        print(SEM_EVIDENCIA.format(pasta))
        return 2

    conta = contar(evidencias)
    print(CABECALHO.format(pasta.name, conta["etapas"], conta["arquivos"]))

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

    print(f"\n{TITULO_REEXECUCAO}")
    codigo, saida = reexecutar(pasta, cwd)
    if codigo is None:
        print(LINHA_SIMPLES.format(saida))
    elif codigo == 0:
        print(LINHA_SIMPLES.format(VERIFICADOR_OK))
    else:
        print(LINHA_SIMPLES.format(VERIFICADOR_ACUSOU.format(codigo)))
        for linha in saida.split("\n")[-12:]:
            print(LINHA_SIMPLES.format(linha))

    print(f"\n{TITULO_SUPOSTO}")
    for lido in supostos(evidencias, conta, codigo in (0, None)):
        print(LINHA_SIMPLES.format(lido))

    houve_falha = conta["para"] > 0 or (codigo not in (0, None))
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


def testar() -> int:
    import tempfile
    falhas = []

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(rotulo)

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
        evidencias = evidencias_da_pasta(boa)
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
        evidencias = evidencias_da_pasta(suja)
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
        evidencias = evidencias_da_pasta(perguntou)
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
             len(evidencias_da_pasta(com_estado)) == 1)
        limpa = evidencias_da_pasta(boa)
        caso("prova que não reproduz vira o suposto mais forte",
             supostos(limpa, contar(limpa), reproduz=False)[0]
             == SUPOSTO_PROVA_NAO_REPRODUZ)
        caso("e quando reproduz, ele não aparece",
             SUPOSTO_PROVA_NAO_REPRODUZ
             not in supostos(limpa, contar(limpa)))

    total = 15
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
    a = ap.parse_args()
    return auditar(Path(a.pasta), a.cwd)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
