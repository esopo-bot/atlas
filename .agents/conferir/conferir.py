#!/usr/bin/env python3
"""conferir — casa o declarado de um recibo com o executado e acusa os dois lados.

DE ONDE VEM "O EXECUTADO" de uma etapa de sessão (a crítica da issue #22
cobrou este nome, e ele fica aqui, às claras):

1. da RE-EXECUÇÃO, aqui e agora, de cada par comando/saida do `provado` —
   o conferir roda o comando de novo, no diretório de trabalho da etapa
   (`--cwd`), acusa exit diferente de 0 e compara o stdout real com a saída
   declarada (o contrato manda a etapa declarar prova re-executável,
   idempotente e de saída estável — está no $comment do provado);
2. do exit code e do structured_output da sessão, que o encadeador já
   materializou por código no recibo (degrau 1) — etapa morta ou recibo
   inválido nem chegam aqui: viraram `para` sintético antes;
3. das EXIGÊNCIAS do manifesto (`--exigir`): o que a etapa DEVIA ter provado.

Os dois lados da acusação:

- **declarado sem executado** — comando do `provado` que, re-executado,
  devolve outra saída, não roda ou estoura o tempo;
- **executado sem declarado** — exigência do manifesto sem item
  correspondente no `provado`. Sem trace de execução da sessão, este lado
  só é acusável pelo que o manifesto exige — dito às claras, não em nota.

O que ele FAZ: valida o recibo contra o contrato (reusa o validador do
recibo.py — regra 3, nada se reimplementa); re-executa o `provado` (tudo,
ou `--amostra N`); confere as exigências; aplica os cheques de conteúdo
herdados do degrau 1 (`segue` sem prova nenhuma; `proximo` banal ou curto;
`pergunta` mais de uma, ou pergunta antes da recomendação); pula recibo
sintético (origem encadeador — skip simétrico: quem não executou não deve
prova); e com `--ensaio` LISTA o que re-executaria sem executar nada.

O que ele NÃO FAZ — e confessa (os refutadores mediram cada limite):
- não protege contra comando destrutivo declarado no `provado` — ele
  RE-EXECUTA o que está declarado; rode a conferência no mesmo isolamento
  da etapa (worktree descartável);
- não distingue prova de eco: `echo "42 passed"` re-executa perfeito para
  sempre — o MÉRITO da prova é do conferente humano e dos portões;
- não autentica recibo sintético: `origem=encadeador` lido do arquivo é
  SUPOSIÇÃO de que só o encadeador escreve ali (a invariante de escritor
  único do degrau 1; o materializar descarta origem/motivo vindos do
  modelo) — forja gravada à mão no disco pula a conferência, e disco
  adulterado está fora do modelo de ameaça desta camada;
- re-executa os itens NA ORDEM: efeito colateral de um item pode fabricar
  o seguinte — prova independente é responsabilidade da etapa (contrato);
- não julga "suposto no mesmo volume" nem o mérito da recomendação; os
  cheques de pergunta/proximo são HEURÍSTICA DE PONTUAÇÃO ("Sr." engana a
  ordem; paráfrase de banalidade escapa) — barram o descuido, não o dolo;
- não compara stderr — a saída declarada é o stdout; comando que sobe
  serviço nunca confere (o filho segura o pipe até o tempo-limite):
  declare a SONDA do serviço, não a subida;
- re-executa no bash quando ele existe (o shell das sessões), senão no
  /bin/sh; exit diferente de 0 acusa — a convenção honesta do grep/diff
  (exit 1 = "não achei"/"é diferente") pede o ` || true` que o $comment
  do contrato ensina;
- não conserta nem escreve recibo (escrever é do encadeador, com recibo.py).

Uso:
    conferir.py recibo <arquivo.json> [opções]
    conferir.py trabalho <pasta-do-trabalho> [opções]
    opções: --cwd D | --amostra N | --exigir TERMO (repetível)
            --ensaio | --tempo-limite SEGUNDOS

Saída: 0 = tudo confere; 4 = acusação (lista no stdout); 2 = erro de
uso ou de ambiente.

Rode os testes com:  python .agents/conferir/conferir.py --testar
"""

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
sys.path.insert(0, str(AQUI.parent / "recibo"))
import recibo as _recibo  # noqa: E402 — o validador e o contrato moram lá

PROXIMO_BANAL = ("tente de novo", "tente novamente", "tenta de novo",
                 "tenta novamente", "tente outra vez", "tente denovo")
PROXIMO_MINIMO = 20  # menos que isto não é instrução, é acenar com a mão

# O que encerra uma frase de recomendação — só "." deixava "Recomendo A!"
# virar acusação falsa (medido pelo refutador).
FIM_DE_FRASE = ".;:!…"
RECOMENDACAO_MINIMA = 15  # "Dúvida:" antes do "?" não é recomendação (medido)

# A re-execução roda no bash quando ele existe — o shell das sessões. Com o
# /bin/sh puro, prova honesta com bashismo saía 127 e virava acusação falsa
# (medido). Sem bash na máquina, cai no /bin/sh e a etapa declara POSIX.
SHELL_DA_REEXECUCAO = shutil.which("bash")

# O nome que o degrau 1 dá a recibo: NN-etapa-cN.json. O modo trabalho só
# olha o que casa — manifesto.json ao lado não é recibo e não vira acusação.
NOME_DE_RECIBO = re.compile(r"[0-9]{2}-[a-z0-9-]+-c[0-9]+\.json\Z")


def _normalizar(texto: str) -> str:
    """Compara sem o ruído de transcrição: CRLF→LF e cada linha sem cauda.

    O rstrip por linha vale para os DOIS lados — transcrição de terminal
    perde espaço de fim de linha, e a leniência de um lado só era
    assimétrica (medido).
    """
    linhas = texto.replace("\r\n", "\n").split("\n")
    return "\n".join(linha.rstrip() for linha in linhas).strip()


def _texto_plano(texto: str) -> str:
    """minúsculo e espaço colapsado — a régua dos cheques de conteúdo."""
    return " ".join(texto.lower().split())


# A etapa anota a LINHA que importa; a re-execução captura tudo. Comparar os
# dois por igualdade acusa a diferença de tamanho como se fosse divergência —
# medido em 18/08/2026: 544 caracteres declarados contra 3.038 re-executados,
# mesmo comando, mesma verdade, acusado. A régua passou a ser: o declarado
# aparece na saída como BLOCO DE LINHAS INTEIRAS E SEGUIDAS.
#
# Por linha, e não por subcadeia, porque subcadeia aceita o que não deve:
# "ok" está dentro de "not ok". Medido nas mesmas evidências: por subcadeia,
# a única acusação que sumiria era justamente a única divergência real.
ELISAO = "(...)"  # a linha com que a etapa declara "cortei um pedaço aqui"


def _blocos_declarados(declarada: str) -> list:
    """A saída declarada, partida nos marcadores de elisão."""
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
    """Cada bloco declarado aparece seguido na saída, e na ordem declarada."""
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


def _confere_saida(real: str, declarada: str, igual: bool) -> bool:
    """A saída declarada confere com a re-executada.

    Declaração VAZIA exige igualdade mesmo sem `--igual`, e isso é o oposto
    de um detalhe: o contrato ensina a fechar prova de ausência com
    `|| true`, então saída vazia é o caso comum, e "contém" a aceitaria
    contra qualquer coisa. Medido: sem esta regra, a única divergência real
    das seis acusações do bloco 2 — um `grep` que passou a achar arquivo —
    viraria silêncio.
    """
    if igual or not declarada:
        return real == declarada
    return _contem_blocos(real, declarada)


def _linha_que_falta(declarada: str, real: str) -> str:
    """Qual linha declarada não apareceu — a acusação sob a régua do contém."""
    presentes = set(real.split("\n"))
    for bloco in _blocos_declarados(declarada):
        for linha in bloco:
            if linha not in presentes:
                return (f"a linha declarada {linha!r} não aparece na saída "
                        f"({len(declarada)} contra {len(real)} caracteres)")
    return ("as linhas declaradas aparecem, mas não seguidas e nesta ordem "
            f"({len(declarada)} contra {len(real)} caracteres) — use "
            f"{ELISAO!r} em linha própria para declarar o corte")


# `grep` na sessão pode não ser o `grep` da re-execução: shell interativo
# carrega perfil, e perfil pode embrulhar o comando num que respeita o
# .gitignore. Mesma linha, dois números — medido em 18/08/2026. A conferência
# não adivinha qual rodou lá: quando acusa divergência num comando com `grep`
# nu, ela AVISA que o binário pode ser a causa. Aviso, não acusação inventada.
_GREP_EXPLICITO = re.compile(r"(?:/(?:usr/)?bin/|command\s+|git\s+)grep\b")
_GREP_NU = re.compile(r"(?<![\w/.-])grep\b")


def _aviso_do_grep(comando: str) -> str:
    if not _GREP_NU.search(_GREP_EXPLICITO.sub("", comando)):
        return ""
    return (" [aviso: o comando usa `grep` sem caminho — a sessão pode ter "
            "rodado um embrulhado, que respeita o .gitignore, e esta "
            "re-execução usou o do PATH. Declare /bin/grep ou git grep]")


def _reexecutar(item: dict, cwd: str, tempo_limite: int,
                igual: bool = False) -> str:
    """Re-executa um item do provado; devolve a acusação, ou '' se confere."""
    try:
        rodada = subprocess.run(item["comando"], shell=True, cwd=cwd,
                                capture_output=True, text=True,
                                timeout=tempo_limite,
                                executable=SHELL_DA_REEXECUCAO)
    except subprocess.TimeoutExpired:
        return (f"não reexecutável em {tempo_limite}s: {item['comando']!r} "
                "— declarado que não se mede aqui")
    except OSError as erro:
        return f"não reexecutável: {item['comando']!r} — {erro}"
    if rodada.returncode != 0:
        # Prova que falha não prova: `false` com saida vazia "conferia"
        # qualquer afirmação de sucesso (medido pelo refutador).
        return (f"comando re-executado falhou (exit {rodada.returncode}): "
                f"{item['comando']!r} — prova declarada termina em 0")
    real = _normalizar(rodada.stdout)
    declarada = _normalizar(item["saida"])
    if not _confere_saida(real, declarada, igual):
        porque = (_onde_diverge(declarada, real) if igual or not declarada
                  else _linha_que_falta(declarada, real))
        return (f"saída diverge em {item['comando']!r}: " + porque
                + _aviso_do_grep(item["comando"]))
    return ""


def _onde_diverge(declarada: str, real: str, janela: int = 60) -> str:
    """Mostra o PONTO da diferença, não os primeiros 80 caracteres de cada.

    Cortar as duas no mesmo tamanho esconde a divergência sempre que ela cai
    depois do corte, e a acusação passa a exibir dois valores idênticos aos
    olhos de quem lê. Medido em 18/08/2026: duas saídas que diferiam só em
    "0.108" contra "0.109", no caractere 118, apareceram como o mesmo texto.
    Acusação que mostra X diferente de X é pior que acusação nenhuma — manda
    procurar justamente o que ela deveria ter apontado.
    """
    i = 0
    while i < min(len(declarada), len(real)) and declarada[i] == real[i]:
        i += 1
    inicio = max(0, i - 12)

    def recorte(texto):
        return (("…" if inicio else "") + texto[inicio:i + janela]
                + ("…" if len(texto) > i + janela else ""))

    return (f"diferem a partir do caractere {i} — declarada "
            f"{recorte(declarada)!r}, agora {recorte(real)!r} "
            f"({len(declarada)} contra {len(real)} caracteres)")


def conferir_recibo(dado: dict, esquema: dict, cwd: str, amostra: int,
                    exigencias: list, ensaio: bool, tempo_limite: int,
                    rotulo: str, igual: bool = False) -> list:
    """Todas as acusações de um recibo; lista vazia = confere."""
    erros = _recibo.validar_recibo(dado, esquema)
    if erros:
        return [f"[{rotulo}] recibo fora do contrato: " + "; ".join(erros[:3])]

    if dado.get("origem") == "encadeador":
        # Sintético: quem não executou não deve prova (skip simétrico) — e
        # o conteúdo dele foi escrito por código já validado no degrau 1.
        return []

    acusacoes = []
    provado = dado["provado"]

    # A regra 2 da camada, instrumentada: segue sem instrumento não é pronto.
    if dado["veredito"] == "segue" and not provado:
        acusacoes.append(f"[{rotulo}] veredito segue com provado vazio — "
                         "só é pronto o que um instrumento provou (regra 2)")

    # Lado 1: declarado sem executado — a re-execução decide. A amostra é
    # DETERMINÍSTICA por conteúdo (semente = hash do recibo): o mesmo recibo
    # dá sempre o mesmo veredito — sem semente era loteria, o mesmo comando
    # ora acusava, ora não (medido). O custo confessado: quem forja
    # conhecendo o algoritmo pode prever a amostra — amostra é troca de
    # custo aceita pelo dono, nunca o padrão (o padrão é tudo).
    itens = provado
    if 0 < amostra < len(provado):
        semente = int(hashlib.sha256(
            json.dumps(dado, sort_keys=True, ensure_ascii=False)
            .encode("utf-8")).hexdigest(), 16)
        itens = random.Random(semente).sample(provado, amostra)
    for item in itens:
        if ensaio:
            print(f"    ensaio: re-executaria {item['comando']!r}")
            continue
        acusacao = _reexecutar(item, cwd, tempo_limite, igual)
        if acusacao:
            acusacoes.append(f"[{rotulo}] {acusacao}")

    # Lado 2: executado sem declarado — o manifesto exige, o provado cala.
    # O termo tem de estar no COMANDO de um item (a prova executável):
    # menção na afirmação satisfazia a exigência sem execução nenhuma, e a
    # concatenação deixava o termo casar atravessando campos (medido).
    for termo in exigencias:
        if not any(_texto_plano(termo) in _texto_plano(item["comando"])
                   for item in provado):
            acusacoes.append(f"[{rotulo}] o manifesto exige {termo!r} e "
                             "nenhum comando do provado o cita — executado "
                             "(ou omitido) sem declaração")

    # Conteúdo herdado do degrau 1: forma o contrato já cobre; mérito é aqui.
    proximo = dado.get("proximo", "")
    if proximo:
        plano = _texto_plano(proximo)
        if any(plano.startswith(banal) for banal in PROXIMO_BANAL):
            acusacoes.append(f"[{rotulo}] proximo começa em banalidade "
                             f"({proximo[:40]!r}) — a regra do contrato: "
                             "nunca 'tente de novo'")
        elif len(plano) < PROXIMO_MINIMO:
            acusacoes.append(f"[{rotulo}] proximo curto demais ({proximo!r}) "
                             "— não é instrução de retomada")
    pergunta = dado.get("pergunta", "")
    if pergunta:
        if "?" not in pergunta:
            acusacoes.append(f"[{rotulo}] campo pergunta sem pergunta "
                             "nenhuma — a regra: uma, com recomendação")
        elif pergunta.count("?") > 1:
            acusacoes.append(f"[{rotulo}] mais de uma pergunta — a regra: "
                             "uma por vez")
        else:
            # A recomendação é o texto antes do primeiro fim-de-frase que
            # preceda o "?" — e precisa de corpo: um "Dúvida:" de seis
            # letras satisfazia a pontuação sem recomendar nada (medido).
            interrogacao = pergunta.find("?")
            fins = [pergunta.find(fim) for fim in FIM_DE_FRASE
                    if 0 <= pergunta.find(fim) < interrogacao]
            recomendacao = pergunta[:min(fins)] if fins else ""
            if len(_texto_plano(recomendacao)) < RECOMENDACAO_MINIMA:
                acusacoes.append(f"[{rotulo}] a pergunta vem antes da "
                                 "recomendação (ou a recomendação não tem "
                                 "corpo) — a regra: recomendação primeiro")
    return acusacoes


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="conferir.py")
    sub = parser.add_subparsers(dest="comando", required=True)

    def comuns(p):
        p.add_argument("alvo")
        p.add_argument("--cwd", default=".",
                       help="diretório de trabalho da etapa (onde re-executar)")
        p.add_argument("--amostra", type=int, default=0,
                       help="re-executa só N itens do provado; 0 = todos")
        p.add_argument("--exigir", action="append", default=[],
                       help="termo que o provado precisa citar (do manifesto)")
        p.add_argument("--ensaio", action="store_true",
                       help="lista o que re-executaria, sem executar nada")
        p.add_argument("--igual", action="store_true",
                       help="exige saída idêntica; o padrão é o declarado "
                            "aparecer na saída como bloco de linhas")
        p.add_argument("--tempo-limite", type=int, default=60)

    comuns(sub.add_parser("recibo", help="confere um recibo"))
    comuns(sub.add_parser("trabalho",
                          help="confere todos os *.json de uma pasta"))
    return parser


def main(argv) -> int:
    args = montar_parser().parse_args(argv)
    esquema = _recibo.carregar_esquema()

    # Erro se trata na fronteira: cwd que não existe é defeito do CHAMADOR
    # (exit 2) — antes, virava acusação falsa contra recibo honesto (medido).
    if not Path(args.cwd).is_dir():
        print(f"erro de uso: --cwd {args.cwd} não existe", file=sys.stderr)
        return 2
    if args.comando == "trabalho" and args.exigir:
        # Exigência é POR ETAPA (vem do manifesto): aplicada à pasta inteira
        # acusava etapa honesta alheia à exigência (medido).
        print("erro de uso: --exigir é por etapa — use o modo recibo, "
              "um arquivo por vez", file=sys.stderr)
        return 2

    alvo = Path(args.alvo)
    if args.comando == "recibo":
        if not alvo.is_file():
            print(f"erro de uso: {alvo} não existe", file=sys.stderr)
            return 2
        arquivos = [alvo]
    else:
        if not alvo.is_dir():
            print(f"erro de uso: {alvo} não é uma pasta de trabalho",
                  file=sys.stderr)
            return 2
        # Só o que tem NOME de recibo do degrau 1 — manifesto.json ao lado
        # não é recibo e não vira acusação (medido). O aviso cobre TODO
        # nome fora do padrão: forja em .JSON escapava sem uma linha porque
        # o glob é sensível a caixa (medido).
        arquivos = sorted(a for a in alvo.iterdir()
                          if NOME_DE_RECIBO.fullmatch(a.name))
        for fora in sorted(alvo.iterdir()):
            if not NOME_DE_RECIBO.fullmatch(fora.name):
                print(f"    ignorado (não tem nome de recibo): {fora.name}")
        if not arquivos:
            print(f"erro de uso: nenhum recibo em {alvo}", file=sys.stderr)
            return 2

    acusacoes = []
    for arquivo in arquivos:
        if not arquivo.is_file():
            # FIFO plantado com nome de recibo pendurava a leitura para
            # sempre e calava a acusação dos vizinhos (medido).
            acusacoes.append(f"[{arquivo.name}] recibo ilegível: "
                             "não é arquivo comum")
            continue
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError) as erro:
            # Recibo ilegível na pasta é ACUSAÇÃO, não parada: abortar aqui
            # descartava as acusações dos vizinhos e o forjador escapava
            # largando um arquivo de lixo ao lado (medido).
            acusacoes.append(f"[{arquivo.name}] recibo ilegível: {erro}")
            continue
        acusacoes += conferir_recibo(dado, esquema, args.cwd, args.amostra,
                                     args.exigir, args.ensaio,
                                     args.tempo_limite, arquivo.name,
                                     args.igual)

    if acusacoes:
        for acusacao in acusacoes:
            print(f"ACUSA {acusacao}")
        print(f"\n{len(acusacoes)} acusações em {len(arquivos)} recibos.")
        return 4
    modo = "ensaio — nada re-executado" if args.ensaio else "re-executado"
    print(f"confere: {len(arquivos)} recibos ({modo}), nenhuma acusação.")
    return 0


# ---------------------------------------------------------------------------
# Os testes: as duas listas (o que confere, o que é acusado) e o
# comportamento — inclusive a forja do pronto-quando e a sentinela do ensaio.
# ---------------------------------------------------------------------------

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


CONFERE = [
    ("provado honesto re-executa igual", _base(), []),
    ("sintético desligada é pulado (skip simétrico)", _base(
        provado=[], origem="encadeador", motivo="desligada",
        faltas=["etapa desligada no manifesto"]), []),
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
    # A etapa anota a linha que importa; a re-execução captura tudo. Era a
    # acusação falsa mais comum — 544 caracteres contra 3.038, medido.
    ("trecho anotado confere contra a saída inteira", _base(provado=[
        {"afirmacao": "o meio da saída é o que importa",
         "comando": r"printf 'cabeçalho\nlinha que importa\nrodapé\n'",
         "saida": "linha que importa"}]), []),
    ("bloco de linhas seguidas confere no meio da saída", _base(provado=[
        {"afirmacao": "duas linhas seguidas",
         "comando": r"printf 'a\nb\nc\nd\n'", "saida": "b\nc"}]), []),
    ("elisão declara o corte e as duas pontas conferem", _base(provado=[
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
    ("recibo fora do contrato", _base(veredito="quase"), [], "fora do contrato"),
    # Os pontos cegos que o "contém" abriria, e que ficam fechados. O
    # primeiro é o mais caro: o contrato ensina a fechar prova de ausência
    # com `|| true`, então saída vazia é o caso COMUM — aceitá-la contra
    # qualquer coisa trocaria cinco gritos errados por um silêncio errado.
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


def _comportamento(pasta, esquema):
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    # a) a forja acusada pela linha de comando, com exit 4 — e o honesto, 0
    forjado = _gravar(pasta, "forja/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o eco responde", "comando": "echo ola",
         "saida": "adeus"}]))
    resposta = _cli(["recibo", str(forjado)])
    caso("forja acusada com exit 4", resposta.returncode == 4
         and "saída diverge" in resposta.stdout)
    honesto = _gravar(pasta, "forja/02-fantoche-c1.json", _base())
    resposta = _cli(["recibo", str(honesto)])
    caso("recibo honesto confere com exit 0", resposta.returncode == 0)

    # b) sentinela do ensaio: com --ensaio NADA executa; sem, executa
    sentinela = Path(pasta) / "sentinela.txt"
    vigiado = _gravar(pasta, "vigia/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "a sentinela grava",
         "comando": f"touch {sentinela} && echo gravou", "saida": "gravou"}]))
    resposta = _cli(["recibo", str(vigiado), "--ensaio"])
    caso("com --ensaio a sentinela NÃO aparece e o ensaio lista o comando",
         not sentinela.exists() and "re-executaria" in resposta.stdout
         and resposta.returncode == 0)
    resposta = _cli(["recibo", str(vigiado)])
    caso("contraprova: sem --ensaio a sentinela aparece",
         sentinela.exists() and resposta.returncode == 0)

    # c) pasta de trabalho inteira: a acusação nomeia o arquivo forjado
    resposta = _cli(["trabalho", str(Path(pasta) / "forja")])
    caso("no trabalho inteiro a acusação nomeia o arquivo",
         resposta.returncode == 4 and "01-fantoche-c1.json" in resposta.stdout
         and "02-fantoche-c1.json" not in resposta.stdout)

    # d) amostra maior que o provado re-executa tudo e ainda acusa
    resposta = _cli(["recibo", str(forjado), "--amostra", "5"])
    caso("amostra maior que o provado ainda acusa", resposta.returncode == 4)

    # e) tempo-limite: comando lento vira acusação, não trava
    lento = _gravar(pasta, "lento/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "dorme", "comando": "sleep 5", "saida": ""}]))
    resposta = _cli(["recibo", str(lento), "--tempo-limite", "1"])
    caso("comando lento acusa por tempo, não trava",
         resposta.returncode == 4 and "não reexecutável" in resposta.stdout)

    # f) alvo que não existe é erro de uso, não acusação
    resposta = _cli(["trabalho", str(Path(pasta) / "nao-existe")])
    caso("pasta inexistente é erro de uso (exit 2)", resposta.returncode == 2)

    # g) pasta mista: lixo ilegível vira acusação e NÃO cala o forjado
    _gravar(pasta, "misto/01-honesta-c1.json", _base())
    _gravar(pasta, "misto/02-forjada-c1.json", _base(provado=[
        {"afirmacao": "eco", "comando": "echo ola", "saida": "adeus"}]))
    (Path(pasta) / "misto" / "03-lixo-c1.json").write_text(
        "{ isto nao e json", encoding="utf-8")
    (Path(pasta) / "misto" / "manifesto.json").write_text(
        "{}", encoding="utf-8")
    resposta = _cli(["trabalho", str(Path(pasta) / "misto")])
    caso("lixo ilegível é acusação e o forjado ao lado ainda é acusado",
         resposta.returncode == 4 and "recibo ilegível" in resposta.stdout
         and "saída diverge" in resposta.stdout)
    caso("manifesto.json ao lado é ignorado, não acusado",
         "ignorado (não tem nome de recibo): manifesto.json"
         in resposta.stdout)

    # h) amostra é determinística: mesmo recibo, mesmo veredito, 3 rodadas
    amostrado = _gravar(pasta, "amostra/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "a", "comando": "echo a", "saida": "a"},
        {"afirmacao": "b", "comando": "echo b", "saida": "b"},
        {"afirmacao": "c", "comando": "echo c", "saida": "FORJADA"}]))
    exits = {_cli(["recibo", str(amostrado), "--amostra", "1"]).returncode
             for _ in range(3)}
    caso("amostra determinística: três rodadas, um só veredito",
         len(exits) == 1)

    # i) fronteiras novas: --exigir no modo trabalho e --cwd fantasma
    resposta = _cli(["trabalho", str(Path(pasta) / "misto"),
                     "--exigir", "echo"])
    caso("--exigir no modo trabalho é erro de uso", resposta.returncode == 2)
    resposta = _cli(["recibo", str(Path(pasta) / "misto/01-honesta-c1.json"),
                     "--cwd", str(Path(pasta) / "nao-existe")])
    caso("--cwd inexistente é erro de uso, não acusação falsa",
         resposta.returncode == 2)

    # j) FIFO plantado com nome de recibo não pendura nem cala os vizinhos
    if hasattr(os, "mkfifo"):
        _gravar(pasta, "fifo/01-forjada-c1.json", _base(provado=[
            {"afirmacao": "eco", "comando": "echo ola", "saida": "adeus"}]))
        os.mkfifo(Path(pasta) / "fifo" / "00-fifo-c1.json")
        resposta = _cli(["trabalho", str(Path(pasta) / "fifo")])
        caso("FIFO vira acusação e a forja vizinha ainda é acusada",
             resposta.returncode == 4
             and "não é arquivo comum" in resposta.stdout
             and "saída diverge" in resposta.stdout)

    # Acusação que corta as duas saídas no mesmo tamanho esconde a diferença
    # quando ela cai depois do corte — e passa a exibir X diferente de X.
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

    # k) forja com extensão .JSON não escapa em silêncio: ganha a linha
    (Path(pasta) / "misto" / "01-forja-c1.JSON").write_text(
        json.dumps(_base()), encoding="utf-8")
    resposta = _cli(["trabalho", str(Path(pasta) / "misto")])
    caso("nome fora do padrão (.JSON) aparece como ignorado",
         "ignorado (não tem nome de recibo): 01-forja-c1.JSON"
         in resposta.stdout)

    # m) --igual restaura a igualdade estrita para quem a quiser
    trecho = _gravar(pasta, "igual/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o meio da saída",
         "comando": r"printf 'antes\nmiolo\ndepois\n'", "saida": "miolo"}]))
    caso("por padrão o trecho anotado confere contra a saída inteira",
         _cli(["recibo", str(trecho)]).returncode == 0)
    resposta = _cli(["recibo", str(trecho), "--igual"])
    caso("com --igual o mesmo trecho volta a ser acusado",
         resposta.returncode == 4 and "saída diverge" in resposta.stdout)
    caso("e a acusação estrita mostra o caractere da divergência",
         "a partir do caractere" in resposta.stdout)

    # n) o aviso do grep vem colado na acusação, e só onde cabe
    nu = _gravar(pasta, "grep/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "não achou nada",
         "comando": "grep -c naoexiste /dev/null || true", "saida": "9"}]))
    resposta = _cli(["recibo", str(nu)])
    caso("acusação de comando com grep nu carrega o aviso do binário",
         resposta.returncode == 4 and "grep` sem caminho" in resposta.stdout)
    explicito = _gravar(pasta, "grep/02-fantoche-c1.json", _base(provado=[
        {"afirmacao": "não achou nada",
         "comando": "/bin/grep -c naoexiste /dev/null || true",
         "saida": "9"}]))
    resposta = _cli(["recibo", str(explicito)])
    caso("com /bin/grep declarado a acusação NÃO carrega o aviso",
         resposta.returncode == 4 and "sem caminho" not in resposta.stdout)

    # o) as funções da régua nova, direto
    caso("bloco seguido é achado no meio", _contem_blocos("a\nb\nc", "b"))
    caso("bloco fora de ordem não é achado",
         not _contem_blocos("a\nb\nc", "c\na"))
    caso("elisão pula o meio", _contem_blocos("a\nb\nc\nd", "a\n(...)\nd"))
    caso("declaração vazia exige igualdade, mesmo sem --igual",
         not _confere_saida("apareceu", "", False)
         and _confere_saida("", "", False))

    # l) bashismo confere quando a máquina tem bash (o shell das sessões)
    if SHELL_DA_REEXECUCAO:
        bashista = _gravar(pasta, "bash/01-fantoche-c1.json", _base(provado=[
            {"afirmacao": "o teste composto do bash roda",
             "comando": "[[ 1 -eq 1 ]] && echo ok", "saida": "ok"}]))
        resposta = _cli(["recibo", str(bashista)])
        caso("bashismo honesto confere no bash", resposta.returncode == 0)

    return resultados


def testar() -> int:
    esquema = _recibo.carregar_esquema()
    falhas = []

    for rotulo, dado, exigencias in CONFERE:
        achadas = conferir_recibo(dado, esquema, ".", 0, exigencias, False,
                                  60, "t")
        if achadas:
            falhas.append(f"CONFERE [{rotulo}]: acusou — {achadas[0]}")

    for rotulo, dado, exigencias, trecho in ACUSA:
        achadas = conferir_recibo(dado, esquema, ".", 0, exigencias, False,
                                  60, "t")
        if not achadas:
            falhas.append(f"ACUSA [{rotulo}]: deixou passar")
        elif not any(trecho in acusacao for acusacao in achadas):
            falhas.append(f"ACUSA [{rotulo}]: acusou pelo motivo errado — "
                          f"{achadas[0]}")

    with tempfile.TemporaryDirectory(prefix="conferir-teste-") as pasta:
        comportamento = _comportamento(pasta, esquema)
    falhas += [f"COMPORTAMENTO [{rotulo}]"
               for rotulo, passou in comportamento if not passou]

    total = len(CONFERE) + len(ACUSA) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — {len(CONFERE)} conferem, {len(ACUSA)} "
          f"acusados, {len(comportamento)} de comportamento")
    return 0


if __name__ == "__main__":
    if "--testar" in sys.argv:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except OSError as ambiente:
        print(f"erro de ambiente: {ambiente}", file=sys.stderr)
        sys.exit(2)
