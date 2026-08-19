import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "evidencia"))
import evidencia as _evidencia

PROXIMO_BANAL = ("tente de novo", "tente novamente", "tenta de novo",
                 "tenta novamente", "tente outra vez", "tente denovo")
PROXIMO_MINIMO = 20
FIM_DE_FRASE = ".;:!…"
RECOMENDACAO_MINIMA = 15
SHELL_DA_REEXECUCAO = shutil.which("bash")
NOME_DE_EVIDENCIA = re.compile(r"[0-9]{2}-[a-z0-9-]+-c[0-9]+\.json\Z")
ORIGEM_SINTETICA = "encadeador"
ELISAO = "(...)"
TEMPO_LIMITE_PADRAO = 60
QUANTAS_ACUSACOES_DO_CONTRATO = 3

GREP_COM_CAMINHO = re.compile(r"(?:/(?:usr/)?bin/|command\s+|git\s+)grep\b")
GREP_NU = re.compile(r"(?<![\w/.-])grep\b")

ROTULADA = "[{}] {}"
ACUSA_FORA_DO_CONTRATO = "evidência fora do contrato: {}"
ACUSA_SEGUE_SEM_PROVA = ("veredito segue com provado vazio — só é pronto o "
                         "que um instrumento provou (regra 2)")
ACUSA_TEMPO_ESGOTADO = ("não reexecutável em {}s: {!r} — declarado que não se "
                        "mede aqui")
ACUSA_NAO_REEXECUTAVEL = "não reexecutável: {!r} — {}"
ACUSA_EXIT_DIFERENTE_DE_ZERO = ("comando re-executado falhou (exit {}): {!r} "
                                "— prova declarada termina em 0")
ACUSA_SAIDA_DIVERGE = "saída diverge em {!r}: {}"
ACUSA_LINHA_AUSENTE = ("a linha declarada {!r} não aparece na saída "
                       "({} contra {} caracteres)")
ACUSA_ORDEM_DAS_LINHAS = ("as linhas declaradas aparecem, mas não seguidas e "
                          "nesta ordem ({} contra {} caracteres) — use {!r} "
                          "em linha própria para declarar o corte")
ACUSA_PONTO_DA_DIVERGENCIA = ("diferem a partir do caractere {} — declarada "
                              "{!r}, agora {!r} ({} contra {} caracteres)")
ACUSA_EXIGENCIA_SEM_COMANDO = ("o roteiro exige {!r} e nenhum comando do "
                               "provado o cita — executado (ou omitido) sem "
                               "declaração")
ACUSA_PROXIMO_BANAL = ("proximo começa em banalidade ({!r}) — a regra do "
                       "contrato: nunca 'tente de novo'")
ACUSA_PROXIMO_CURTO = ("proximo curto demais ({!r}) — não é instrução de "
                       "retomada")
ACUSA_PERGUNTA_SEM_PERGUNTA = ("campo pergunta sem pergunta nenhuma — a "
                               "regra: uma, com recomendação")
ACUSA_MAIS_DE_UMA_PERGUNTA = "mais de uma pergunta — a regra: uma por vez"
ACUSA_RECOMENDACAO_DEPOIS = ("a pergunta vem antes da recomendação (ou a "
                             "recomendação não tem corpo) — a regra: "
                             "recomendação primeiro")
ACUSA_NAO_E_ARQUIVO_COMUM = "evidência ilegível: não é arquivo comum"
ACUSA_EVIDENCIA_ILEGIVEL = "evidência ilegível: {}"

AVISO_DO_GREP = (" [aviso: o comando usa `grep` sem caminho — a sessão pode "
                 "ter rodado um embrulhado, que respeita o .gitignore, e esta "
                 "re-execução usou o do PATH. Declare /bin/grep ou git grep]")

LINHA_DO_ENSAIO = "    ensaio: re-executaria {!r}"
LINHA_IGNORADO = "    ignorado (não tem nome de evidência): {}"
LINHA_ACUSA = "ACUSA {}"
RESUMO_ACUSACOES = "\n{} acusações em {} evidências."
RESUMO_TUDO_BATE = "tudo bate: {} evidências ({}), nenhuma acusação."
MODO_ENSAIO = "ensaio — nada re-executado"
MODO_REEXECUTADO = "re-executado"

ERRO_CWD_INEXISTENTE = "erro de uso: --cwd {} não existe"
ERRO_EXIGIR_POR_ETAPA = ("erro de uso: --exigir é por etapa — use o modo "
                         "evidência, um arquivo por vez")
ERRO_ALVO_INEXISTENTE = "erro de uso: {} não existe"
ERRO_ALVO_NAO_E_PASTA = "erro de uso: {} não é uma pasta de trabalho"
ERRO_PASTA_SEM_EVIDENCIA = "erro de uso: nenhuma evidência em {}"
ERRO_DE_AMBIENTE = "erro de ambiente: {}"

AJUDA_MODO_EVIDENCIA = "verifica uma evidência"
AJUDA_MODO_TRABALHO = "verifica todos os *.json de uma pasta"
AJUDA_CWD = "diretório de trabalho da etapa (onde re-executar)"
AJUDA_AMOSTRA = "re-executa só N itens do provado; 0 = todos"
AJUDA_EXIGIR = "termo que o provado precisa citar (do roteiro)"
AJUDA_ENSAIO = "lista o que re-executaria, sem executar nada"
AJUDA_IGUAL = ("exige saída idêntica; o padrão é o declarado aparecer na "
               "saída como bloco de linhas")

TESTE_BATE_ACUSOU = "BATE [{}]: acusou — {}"
TESTE_ACUSA_DEIXOU_PASSAR = "ACUSA [{}]: deixou passar"
TESTE_ACUSA_MOTIVO_ERRADO = "ACUSA [{}]: acusou pelo motivo errado — {}"
TESTE_COMPORTAMENTO = "COMPORTAMENTO [{}]"
TESTE_FALHA = "FALHOU: {}"
TESTE_RESUMO_FALHA = "FALHOU: {} de {} casos"
TESTE_RESUMO_OK = ("OK: {} casos — {} batem, {} acusados, {} de "
                   "comportamento")


def _normalizar(texto: str) -> str:
    linhas = texto.replace("\r\n", "\n").split("\n")
    return "\n".join(linha.rstrip() for linha in linhas).strip()


def _texto_plano(texto: str) -> str:
    return " ".join(texto.lower().split())


def _blocos_declarados(declarada: str) -> list:
    blocos, atual = [], []
    for linha in declarada.split("\n"):
        if linha.strip() == ELISAO:
            if atual:
                blocos.append(atual)
            atual = []
        else:
            atual.append(linha)
    if atual:
        blocos.append(atual)
    return blocos


def _contem_blocos(real: str, declarada: str) -> bool:
    linhas = real.split("\n")
    inicio = 0
    for bloco in _blocos_declarados(declarada):
        tamanho = len(bloco)
        achou = -1
        for i in range(inicio, len(linhas) - tamanho + 1):
            if linhas[i:i + tamanho] == bloco:
                achou = i
                break
        if achou < 0:
            return False
        inicio = achou + tamanho
    return True


def _verifica_saida(real: str, declarada: str, igual: bool) -> bool:
    if igual or not declarada:
        return real == declarada
    return _contem_blocos(real, declarada)


def _linha_que_falta(declarada: str, real: str) -> str:
    presentes = set(real.split("\n"))
    for bloco in _blocos_declarados(declarada):
        for linha in bloco:
            if linha not in presentes:
                return ACUSA_LINHA_AUSENTE.format(linha, len(declarada),
                                                  len(real))
    return ACUSA_ORDEM_DAS_LINHAS.format(len(declarada), len(real), ELISAO)


def _aviso_do_grep(comando: str) -> str:
    if not GREP_NU.search(GREP_COM_CAMINHO.sub("", comando)):
        return ""
    return AVISO_DO_GREP


def _onde_diverge(declarada: str, real: str, janela: int = 60) -> str:
    i = 0
    while i < min(len(declarada), len(real)) and declarada[i] == real[i]:
        i += 1
    inicio = max(0, i - 12)

    def recorte(texto):
        return (("…" if inicio else "") + texto[inicio:i + janela]
                + ("…" if len(texto) > i + janela else ""))

    return ACUSA_PONTO_DA_DIVERGENCIA.format(i, recorte(declarada),
                                             recorte(real), len(declarada),
                                             len(real))


def _porque_diverge(declarada: str, real: str, igual: bool) -> str:
    if igual or not declarada:
        return _onde_diverge(declarada, real)
    return _linha_que_falta(declarada, real)


def _reexecutar(item: dict, cwd: str, tempo_limite: int,
                igual: bool = False) -> str:
    try:
        rodada = subprocess.run(item["comando"], shell=True, cwd=cwd,
                                capture_output=True, text=True,
                                timeout=tempo_limite,
                                executable=SHELL_DA_REEXECUCAO)
    except subprocess.TimeoutExpired:
        return ACUSA_TEMPO_ESGOTADO.format(tempo_limite, item["comando"])
    except OSError as erro:
        return ACUSA_NAO_REEXECUTAVEL.format(item["comando"], erro)
    if rodada.returncode != 0:
        return ACUSA_EXIT_DIFERENTE_DE_ZERO.format(rodada.returncode,
                                                   item["comando"])
    real = _normalizar(rodada.stdout)
    declarada = _normalizar(item["saida"])
    if not _verifica_saida(real, declarada, igual):
        return (ACUSA_SAIDA_DIVERGE.format(
            item["comando"], _porque_diverge(declarada, real, igual))
            + _aviso_do_grep(item["comando"]))
    return ""


def _sintetica_do_encadeador(dado: dict) -> bool:
    return dado.get("origem") == ORIGEM_SINTETICA


def _amostra_deterministica(dado: dict, provado: list, quantos: int) -> list:
    if not 0 < quantos < len(provado):
        return provado
    semente = int(hashlib.sha256(
        json.dumps(dado, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest(), 16)
    return random.Random(semente).sample(provado, quantos)


def _acusacoes_da_reexecucao(itens: list, cwd: str, tempo_limite: int,
                             igual: bool, ensaio: bool, rotulo: str) -> list:
    acusacoes = []
    for item in itens:
        if ensaio:
            print(LINHA_DO_ENSAIO.format(item["comando"]))
            continue
        acusacao = _reexecutar(item, cwd, tempo_limite, igual)
        if acusacao:
            acusacoes.append(ROTULADA.format(rotulo, acusacao))
    return acusacoes


def _acusacoes_das_exigencias(provado: list, exigencias: list,
                              rotulo: str) -> list:
    acusacoes = []
    for termo in exigencias:
        if not any(_texto_plano(termo) in _texto_plano(item["comando"])
                   for item in provado):
            acusacoes.append(ROTULADA.format(
                rotulo, ACUSA_EXIGENCIA_SEM_COMANDO.format(termo)))
    return acusacoes


def _acusacoes_do_proximo(proximo: str, rotulo: str) -> list:
    if not proximo:
        return []
    plano = _texto_plano(proximo)
    if any(plano.startswith(banal) for banal in PROXIMO_BANAL):
        return [ROTULADA.format(rotulo,
                                ACUSA_PROXIMO_BANAL.format(proximo[:40]))]
    if len(plano) < PROXIMO_MINIMO:
        return [ROTULADA.format(rotulo, ACUSA_PROXIMO_CURTO.format(proximo))]
    return []


def _recomendacao_antes_da_pergunta(pergunta: str) -> str:
    interrogacao = pergunta.find("?")
    fins = [pergunta.find(fim) for fim in FIM_DE_FRASE
            if 0 <= pergunta.find(fim) < interrogacao]
    return pergunta[:min(fins)] if fins else ""


def _acusacoes_da_pergunta(pergunta: str, rotulo: str) -> list:
    if not pergunta:
        return []
    if "?" not in pergunta:
        return [ROTULADA.format(rotulo, ACUSA_PERGUNTA_SEM_PERGUNTA)]
    if pergunta.count("?") > 1:
        return [ROTULADA.format(rotulo, ACUSA_MAIS_DE_UMA_PERGUNTA)]
    recomendacao = _recomendacao_antes_da_pergunta(pergunta)
    if len(_texto_plano(recomendacao)) < RECOMENDACAO_MINIMA:
        return [ROTULADA.format(rotulo, ACUSA_RECOMENDACAO_DEPOIS)]
    return []


def verificar_evidencia(dado: dict, esquema: dict, cwd: str, amostra: int,
                        exigencias: list, ensaio: bool, tempo_limite: int,
                        rotulo: str, igual: bool = False) -> list:
    erros = _evidencia.validar_evidencia(dado, esquema)
    if erros:
        juntos = "; ".join(erros[:QUANTAS_ACUSACOES_DO_CONTRATO])
        return [ROTULADA.format(rotulo, ACUSA_FORA_DO_CONTRATO.format(juntos))]

    if _sintetica_do_encadeador(dado):
        return []

    provado = dado["provado"]
    acusacoes = []
    if dado["veredito"] == "segue" and not provado:
        acusacoes.append(ROTULADA.format(rotulo, ACUSA_SEGUE_SEM_PROVA))
    acusacoes += _acusacoes_da_reexecucao(
        _amostra_deterministica(dado, provado, amostra),
        cwd, tempo_limite, igual, ensaio, rotulo)
    acusacoes += _acusacoes_das_exigencias(provado, exigencias, rotulo)
    acusacoes += _acusacoes_do_proximo(dado.get("proximo", ""), rotulo)
    acusacoes += _acusacoes_da_pergunta(dado.get("pergunta", ""), rotulo)
    return acusacoes


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verificar.py")
    sub = parser.add_subparsers(dest="comando", required=True)

    def comuns(p):
        p.add_argument("alvo")
        p.add_argument("--cwd", default=".", help=AJUDA_CWD)
        p.add_argument("--amostra", type=int, default=0, help=AJUDA_AMOSTRA)
        p.add_argument("--exigir", action="append", default=[],
                       help=AJUDA_EXIGIR)
        p.add_argument("--ensaio", action="store_true", help=AJUDA_ENSAIO)
        p.add_argument("--igual", action="store_true", help=AJUDA_IGUAL)
        p.add_argument("--tempo-limite", type=int,
                       default=TEMPO_LIMITE_PADRAO)

    comuns(sub.add_parser("evidencia", help=AJUDA_MODO_EVIDENCIA))
    comuns(sub.add_parser("trabalho", help=AJUDA_MODO_TRABALHO))
    return parser


def _evidencias_da_pasta(alvo: Path) -> list:
    arquivos = sorted(a for a in alvo.iterdir()
                      if NOME_DE_EVIDENCIA.fullmatch(a.name))
    for fora in sorted(alvo.iterdir()):
        if not NOME_DE_EVIDENCIA.fullmatch(fora.name):
            print(LINHA_IGNORADO.format(fora.name))
    return arquivos


def _acusacoes_dos_arquivos(arquivos: list, esquema: dict, args) -> list:
    acusacoes = []
    for arquivo in arquivos:
        if not arquivo.is_file():
            acusacoes.append(ROTULADA.format(arquivo.name,
                                             ACUSA_NAO_E_ARQUIVO_COMUM))
            continue
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError) as erro:
            acusacoes.append(ROTULADA.format(
                arquivo.name, ACUSA_EVIDENCIA_ILEGIVEL.format(erro)))
            continue
        acusacoes += verificar_evidencia(dado, esquema, args.cwd, args.amostra,
                                         args.exigir, args.ensaio,
                                         args.tempo_limite, arquivo.name,
                                         args.igual)
    return acusacoes


def _dizer_o_veredito(acusacoes: list, quantas_evidencias: int,
                      ensaio: bool) -> int:
    if acusacoes:
        for acusacao in acusacoes:
            print(LINHA_ACUSA.format(acusacao))
        print(RESUMO_ACUSACOES.format(len(acusacoes), quantas_evidencias))
        return 4
    print(RESUMO_TUDO_BATE.format(quantas_evidencias,
                                  MODO_ENSAIO if ensaio else MODO_REEXECUTADO))
    return 0


def main(argv) -> int:
    args = montar_parser().parse_args(argv)
    esquema = _evidencia.carregar_esquema()

    if not Path(args.cwd).is_dir():
        print(ERRO_CWD_INEXISTENTE.format(args.cwd), file=sys.stderr)
        return 2
    if args.comando == "trabalho" and args.exigir:
        print(ERRO_EXIGIR_POR_ETAPA, file=sys.stderr)
        return 2

    alvo = Path(args.alvo)
    if args.comando == "evidencia":
        if not alvo.is_file():
            print(ERRO_ALVO_INEXISTENTE.format(alvo), file=sys.stderr)
            return 2
        arquivos = [alvo]
    else:
        if not alvo.is_dir():
            print(ERRO_ALVO_NAO_E_PASTA.format(alvo), file=sys.stderr)
            return 2
        arquivos = _evidencias_da_pasta(alvo)
        if not arquivos:
            print(ERRO_PASTA_SEM_EVIDENCIA.format(alvo), file=sys.stderr)
            return 2

    return _dizer_o_veredito(_acusacoes_dos_arquivos(arquivos, esquema, args),
                             len(arquivos), args.ensaio)


def _base(**troca):
    dado = {
        "etapa": "fantoche", "trabalho": "issue-0",
        "quando": "2026-08-16T12:00:00-03:00", "veredito": "segue",
        "provado": [{"afirmacao": "o eco responde",
                     "comando": "echo ola", "saida": "ola"}],
        "suposto": [], "faltas": [],
        "ciclo": {"i": 1, "teto": 3},
    }
    dado.update(troca)
    return dado


BATE = [
    ("provado honesto re-executa igual", _base(), []),
    ("sintético desligada é pulado (skip simétrico)", _base(
        provado=[], origem="encadeador", motivo="desligada",
        faltas=["etapa desligada no roteiro"]), []),
    ("para com proximo decente e sem prova", _base(
        veredito="para", provado=[],
        faltas=["faltou a paginação pedida"],
        proximo="Implemente a paginação pedida na issue e prove com a "
                "página 2 diferente da 1."), []),
    ("pergunta com a recomendação primeiro", _base(
        veredito="pergunta",
        pergunta="Recomendo A porque custa um comando. Sigo com A?"), []),
    ("pergunta com recomendação terminada em exclamação", _base(
        veredito="pergunta",
        pergunta="Recomendo A porque custa um comando! Sigo com A?"), []),
    ("exigência presente no provado", _base(), ["echo"]),
    ("exigência sem caixa e com espaço a mais", _base(), ["Echo"]),
    ("proximo que cita a banalidade no meio de instrução real", _base(
        veredito="para",
        proximo="Se falhar, tente de novo com o venv ativo e rode o lint "
                "antes de reabrir."), []),
    ("contraprova negativa com a convenção do || true", _base(provado=[
        {"afirmacao": "não há segredo no arquivo",
         "comando": "grep -c segredo /dev/null || true", "saida": "0"}]), []),
    ("trecho anotado bate contra a saída inteira", _base(provado=[
        {"afirmacao": "o meio da saída é o que importa",
         "comando": r"printf 'cabeçalho\nlinha que importa\nrodapé\n'",
         "saida": "linha que importa"}]), []),
    ("bloco de linhas seguidas bate no meio da saída", _base(provado=[
        {"afirmacao": "duas linhas seguidas",
         "comando": r"printf 'a\nb\nc\nd\n'", "saida": "b\nc"}]), []),
    ("elisão declara o corte e as duas pontas batem", _base(provado=[
        {"afirmacao": "começo e fim, com o meio cortado",
         "comando": r"printf 'a\nb\nc\nd\n'",
         "saida": "a\n(...)\nd"}]), []),
]

ACUSA = [
    ("saída forjada — o pronto-quando do degrau", _base(provado=[
        {"afirmacao": "o eco responde", "comando": "echo ola",
         "saida": "adeus"}]), [], "saída diverge"),
    ("comando que não roda", _base(provado=[
        {"afirmacao": "roda", "comando": "comando-que-nao-existe-xyz 2>/dev/null",
         "saida": "ok"}]), [], "falhou (exit"),
    ("comando que falha não prova sucesso", _base(provado=[
        {"afirmacao": "a validação passa", "comando": "false",
         "saida": ""}]), [], "falhou (exit"),
    ("segue sem prova nenhuma (regra 2)", _base(provado=[]), [], "regra 2"),
    ("exigência ausente do provado", _base(), ["mcp-sonda"],
     "nenhum comando"),
    ("exigência citada só na afirmação não vale", _base(provado=[
        {"afirmacao": "rodei pytest -q e passou tudo", "comando": "echo ok",
         "saida": "ok"}]), ["pytest"], "nenhum comando"),
    ("pergunta sem interrogação nenhuma", _base(
        veredito="pergunta", pergunta="Diga se sigo com A ou com B"),
     [], "sem pergunta"),
    ("dois-pontos sem recomendação de verdade", _base(
        veredito="pergunta", pergunta="Dúvida: sigo com A ou com B?"),
     [], "recomendação"),
    ("proximo banal", _base(veredito="para", proximo="Tente de novo."),
     [], "nunca 'tente de novo'"),
    ("proximo curto demais", _base(veredito="para", proximo="conserte isto"),
     [], "curto demais"),
    ("duas perguntas", _base(veredito="pergunta",
                             pergunta="Recomendo A. Sigo? Ou paro?"),
     [], "mais de uma"),
    ("pergunta antes da recomendação", _base(
        veredito="pergunta", pergunta="Sigo com A? Recomendo A."),
     [], "recomendação primeiro"),
    ("evidência fora do contrato", _base(veredito="quase"), [], "fora do contrato"),
    ("saída vazia declarada não aceita saída que apareceu", _base(provado=[
        {"afirmacao": "não achou nada", "comando": "echo achou",
         "saida": ""}]), [], "saída diverge"),
    ("contém é por linha inteira: 'ok' não passa dentro de 'not ok'",
     _base(provado=[{"afirmacao": "passou", "comando": "echo 'not ok'",
                     "saida": "ok"}]), [], "não aparece na saída"),
    ("linha declarada que não existe na saída ainda acusa", _base(provado=[
        {"afirmacao": "tem a linha", "comando": r"printf 'a\nb\n'",
         "saida": "z"}]), [], "não aparece na saída"),
    ("linhas certas fora da ordem declarada acusam", _base(provado=[
        {"afirmacao": "duas linhas", "comando": r"printf 'a\nb\nc\n'",
         "saida": "c\na"}]), [], "saída diverge"),
]


def _cli(argumentos):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + argumentos,
        capture_output=True, text=True, timeout=120)


def _gravar(pasta, nome, dado):
    caminho = Path(pasta) / nome
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
    return caminho


def _a_forja_e_acusada_com_exit_4(pasta, caso):
    forjado = _gravar(pasta, "forja/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o eco responde", "comando": "echo ola",
         "saida": "adeus"}]))
    resposta = _cli(["evidencia", str(forjado)])
    caso("forja acusada com exit 4", resposta.returncode == 4
         and "saída diverge" in resposta.stdout)
    honesto = _gravar(pasta, "forja/02-fantoche-c1.json", _base())
    resposta = _cli(["evidencia", str(honesto)])
    caso("evidência honesta bate com exit 0", resposta.returncode == 0)


def _o_ensaio_nao_executa_nada(pasta, caso):
    sentinela = Path(pasta) / "sentinela.txt"
    vigiado = _gravar(pasta, "vigia/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "a sentinela grava",
         "comando": f"touch {sentinela} && echo gravou", "saida": "gravou"}]))
    resposta = _cli(["evidencia", str(vigiado), "--ensaio"])
    caso("com --ensaio a sentinela NÃO aparece e o ensaio lista o comando",
         not sentinela.exists() and "re-executaria" in resposta.stdout
         and resposta.returncode == 0)
    resposta = _cli(["evidencia", str(vigiado)])
    caso("contraprova: sem --ensaio a sentinela aparece",
         sentinela.exists() and resposta.returncode == 0)


def _o_trabalho_inteiro_nomeia_o_forjado(pasta, caso):
    resposta = _cli(["trabalho", str(Path(pasta) / "forja")])
    caso("no trabalho inteiro a acusação nomeia o arquivo",
         resposta.returncode == 4 and "01-fantoche-c1.json" in resposta.stdout
         and "02-fantoche-c1.json" not in resposta.stdout)
    forjado = Path(pasta) / "forja" / "01-fantoche-c1.json"
    resposta = _cli(["evidencia", str(forjado), "--amostra", "5"])
    caso("amostra maior que o provado ainda acusa", resposta.returncode == 4)


def _comando_lento_acusa_por_tempo(pasta, caso):
    lento = _gravar(pasta, "lento/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "dorme", "comando": "sleep 5", "saida": ""}]))
    resposta = _cli(["evidencia", str(lento), "--tempo-limite", "1"])
    caso("comando lento acusa por tempo, não trava",
         resposta.returncode == 4 and "não reexecutável" in resposta.stdout)
    resposta = _cli(["trabalho", str(Path(pasta) / "nao-existe")])
    caso("pasta inexistente é erro de uso (exit 2)", resposta.returncode == 2)


def _o_lixo_ilegivel_nao_cala_os_vizinhos(pasta, caso):
    _gravar(pasta, "misto/01-honesta-c1.json", _base())
    _gravar(pasta, "misto/02-forjada-c1.json", _base(provado=[
        {"afirmacao": "eco", "comando": "echo ola", "saida": "adeus"}]))
    (Path(pasta) / "misto" / "03-lixo-c1.json").write_text(
        "{ isto nao e json", encoding="utf-8")
    (Path(pasta) / "misto" / "roteiro.json").write_text(
        "{}", encoding="utf-8")
    resposta = _cli(["trabalho", str(Path(pasta) / "misto")])
    caso("lixo ilegível é acusação e o forjado ao lado ainda é acusado",
         resposta.returncode == 4 and "evidência ilegível" in resposta.stdout
         and "saída diverge" in resposta.stdout)
    caso("roteiro.json ao lado é ignorado, não acusado",
         "ignorado (não tem nome de evidência): roteiro.json"
         in resposta.stdout)


def _a_amostra_e_deterministica(pasta, caso):
    amostrado = _gravar(pasta, "amostra/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "a", "comando": "echo a", "saida": "a"},
        {"afirmacao": "b", "comando": "echo b", "saida": "b"},
        {"afirmacao": "c", "comando": "echo c", "saida": "FORJADA"}]))
    exits = {_cli(["evidencia", str(amostrado), "--amostra", "1"]).returncode
             for _ in range(3)}
    caso("amostra determinística: três rodadas, um só veredito",
         len(exits) == 1)


def _as_fronteiras_de_uso(pasta, caso):
    resposta = _cli(["trabalho", str(Path(pasta) / "misto"),
                     "--exigir", "echo"])
    caso("--exigir no modo trabalho é erro de uso", resposta.returncode == 2)
    resposta = _cli(["evidencia", str(Path(pasta) / "misto/01-honesta-c1.json"),
                     "--cwd", str(Path(pasta) / "nao-existe")])
    caso("--cwd inexistente é erro de uso, não acusação falsa",
         resposta.returncode == 2)


def _o_fifo_nao_pendura_nem_cala(pasta, caso):
    if not hasattr(os, "mkfifo"):
        return
    _gravar(pasta, "fifo/01-forjada-c1.json", _base(provado=[
        {"afirmacao": "eco", "comando": "echo ola", "saida": "adeus"}]))
    os.mkfifo(Path(pasta) / "fifo" / "00-fifo-c1.json")
    resposta = _cli(["trabalho", str(Path(pasta) / "fifo")])
    caso("FIFO vira acusação e a forja vizinha ainda é acusada",
         resposta.returncode == 4
         and "não é arquivo comum" in resposta.stdout
         and "saída diverge" in resposta.stdout)


def _a_acusacao_aponta_onde_diverge(caso):
    longa = "x" * 100 + "0.108"
    outra = "x" * 100 + "0.109"
    aponta = _onde_diverge(longa, outra)
    caso("a acusação diz em que caractere as saídas divergem",
         "caractere 104" in aponta)
    caso("e o recorte mostra os dois lados DIFERENTES",
         "0.108" in aponta and "0.109" in aponta)
    caso("e conta o tamanho de cada uma", "105 contra 105" in aponta)
    caso("diferença no começo também é apontada",
         "caractere 0" in _onde_diverge("abc", "zbc"))
    caso("sobra no fim é apontada pelo tamanho",
         "3 contra 5" in _onde_diverge("abc", "abcde"))


def _nome_fora_do_padrao_aparece_como_ignorado(pasta, caso):
    (Path(pasta) / "misto" / "01-forja-c1.JSON").write_text(
        json.dumps(_base()), encoding="utf-8")
    resposta = _cli(["trabalho", str(Path(pasta) / "misto")])
    caso("nome fora do padrão (.JSON) aparece como ignorado",
         "ignorado (não tem nome de evidência): 01-forja-c1.JSON"
         in resposta.stdout)


def _igual_restaura_a_igualdade_estrita(pasta, caso):
    trecho = _gravar(pasta, "igual/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o meio da saída",
         "comando": r"printf 'antes\nmiolo\ndepois\n'", "saida": "miolo"}]))
    caso("por padrão o trecho anotado bate contra a saída inteira",
         _cli(["evidencia", str(trecho)]).returncode == 0)
    resposta = _cli(["evidencia", str(trecho), "--igual"])
    caso("com --igual o mesmo trecho volta a ser acusado",
         resposta.returncode == 4 and "saída diverge" in resposta.stdout)
    caso("e a acusação estrita mostra o caractere da divergência",
         "a partir do caractere" in resposta.stdout)


def _o_aviso_do_grep_so_onde_cabe(pasta, caso):
    nu = _gravar(pasta, "grep/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "não achou nada",
         "comando": "grep -c naoexiste /dev/null || true", "saida": "9"}]))
    resposta = _cli(["evidencia", str(nu)])
    caso("acusação de comando com grep nu carrega o aviso do binário",
         resposta.returncode == 4 and "grep` sem caminho" in resposta.stdout)
    explicito = _gravar(pasta, "grep/02-fantoche-c1.json", _base(provado=[
        {"afirmacao": "não achou nada",
         "comando": "/bin/grep -c naoexiste /dev/null || true",
         "saida": "9"}]))
    resposta = _cli(["evidencia", str(explicito)])
    caso("com /bin/grep declarado a acusação NÃO carrega o aviso",
         resposta.returncode == 4 and "sem caminho" not in resposta.stdout)


def _a_regua_do_contem(caso):
    caso("bloco seguido é achado no meio", _contem_blocos("a\nb\nc", "b"))
    caso("bloco fora de ordem não é achado",
         not _contem_blocos("a\nb\nc", "c\na"))
    caso("elisão pula o meio", _contem_blocos("a\nb\nc\nd", "a\n(...)\nd"))
    caso("declaração vazia exige igualdade, mesmo sem --igual",
         not _verifica_saida("apareceu", "", False)
         and _verifica_saida("", "", False))


def _o_bashismo_bate_no_bash(pasta, caso):
    if not SHELL_DA_REEXECUCAO:
        return
    bashista = _gravar(pasta, "bash/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o teste composto do bash roda",
         "comando": "[[ 1 -eq 1 ]] && echo ok", "saida": "ok"}]))
    resposta = _cli(["evidencia", str(bashista)])
    caso("bashismo honesto bate no bash", resposta.returncode == 0)


def _comportamento(pasta):
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    _a_forja_e_acusada_com_exit_4(pasta, caso)
    _o_ensaio_nao_executa_nada(pasta, caso)
    _o_trabalho_inteiro_nomeia_o_forjado(pasta, caso)
    _comando_lento_acusa_por_tempo(pasta, caso)
    _o_lixo_ilegivel_nao_cala_os_vizinhos(pasta, caso)
    _a_amostra_e_deterministica(pasta, caso)
    _as_fronteiras_de_uso(pasta, caso)
    _o_fifo_nao_pendura_nem_cala(pasta, caso)
    _a_acusacao_aponta_onde_diverge(caso)
    _nome_fora_do_padrao_aparece_como_ignorado(pasta, caso)
    _igual_restaura_a_igualdade_estrita(pasta, caso)
    _o_aviso_do_grep_so_onde_cabe(pasta, caso)
    _a_regua_do_contem(caso)
    _o_bashismo_bate_no_bash(pasta, caso)
    return resultados


def testar() -> int:
    esquema = _evidencia.carregar_esquema()
    falhas = []

    for rotulo, dado, exigencias in BATE:
        achadas = verificar_evidencia(dado, esquema, ".", 0, exigencias,
                                      False, 60, "t")
        if achadas:
            falhas.append(TESTE_BATE_ACUSOU.format(rotulo, achadas[0]))

    for rotulo, dado, exigencias, trecho in ACUSA:
        achadas = verificar_evidencia(dado, esquema, ".", 0, exigencias,
                                      False, 60, "t")
        if not achadas:
            falhas.append(TESTE_ACUSA_DEIXOU_PASSAR.format(rotulo))
        elif not any(trecho in acusacao for acusacao in achadas):
            falhas.append(TESTE_ACUSA_MOTIVO_ERRADO.format(rotulo, achadas[0]))

    with tempfile.TemporaryDirectory(prefix="verificar-teste-") as pasta:
        comportamento = _comportamento(pasta)
    falhas += [TESTE_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]

    total = len(BATE) + len(ACUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(TESTE_FALHA.format(falha))
        print(TESTE_RESUMO_FALHA.format(len(falhas), total))
        return 1
    print(TESTE_RESUMO_OK.format(total, len(BATE), len(ACUSA),
                                 len(comportamento)))
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(ERRO_DE_AMBIENTE.format(ambiente), file=sys.stderr)
        sys.exit(2)
