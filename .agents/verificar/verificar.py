import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
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
ETAPA_DA_VERIFICACAO = "verificacao"
NOME_DA_VERIFICACAO = re.compile(
    r"[0-9]{2}-" + ETAPA_DA_VERIFICACAO + r"-c[0-9]+\.json\Z")
ORIGEM_SINTETICA = "encadeador"
ELISAO = "(...)"
TEMPO_LIMITE_PADRAO = 60
CAMPO_DO_TEMPO_LIMITE = "tempo-limite"
QUANTAS_ACUSACOES_DO_CONTRATO = 3
ENTRADA_PADRAO = "-"
NAO_E_OBJETO = "não é objeto de evidência"
CRITERIO_ABERTO = re.compile(r"^[ \t]*[-*][ \t]+\[ \][ \t]+(\S.*?)[ \t]*$",
                             re.MULTILINE)
CABECALHO_DE_SECAO = re.compile(r"^[ \t]*##(?!#)")
SECAO_DE_UM_BLOCO = re.compile(r"^[ \t]*##[ \t]+Bloco[ \t]+([0-9]+)\b",
                               re.IGNORECASE)
FORA_DO_TERMO = re.compile(r"[^0-9a-z]+")
TAMANHO_MINIMO_DO_TERMO = 4
LIMITE_DO_CRITERIO = 120
LIMITE_DOS_TERMOS = 6
CAMPOS_DA_PROVA = ("afirmacao", "comando", "saida")
CAMPOS_QUE_RESPONDEM = ("suposto",)
BANAIS = frozenset("""
para como cada mais menos esta este essa esse isso isto aqui dele dela deles
delas pelo pela onde quando porque ainda todo toda todos todas entre sobre
antes depois quem seja sejam sendo mesmo mesma outro outra outros outras
muito pouco nunca sempre tambem apenas entao assim fica ficam vira viram
pode podem deve devem fazer nada tudo qual quais uma umas
""".split())

GREP_COM_CAMINHO = re.compile(r"(?:/(?:usr/)?bin/|command\s+|git\s+)grep\b")
GREP_NU = re.compile(r"(?<![\w/.-])grep\b")

ROTULADA = "[{}] {}"
ACUSA_FORA_DO_CONTRATO = "evidência fora do contrato: {}"
ACUSA_SEGUE_SEM_PROVA = ("veredito segue com provado vazio — só é pronto o "
                         "que um instrumento provou (regra 2)")
ACUSA_TEMPO_ESGOTADO = (
    "tempo esgotado em {teto}s, sem chegar a comparar a saída: {comando!r} — "
    "prova lenta não é prova errada, e este teto não diz nada sobre o que ela "
    "mediu. Se o comando termina, declare o teto dele no próprio item do "
    "provado:\n"
    '    "{campo}": <segundos>\n'
    "e só aquele item ganha o tempo; `--{campo} <segundos>` dá o mesmo teto a "
    "todos. Se o comando não termina, aí é defeito da prova — o teto existe "
    "para isso.")
ACUSA_NAO_REEXECUTAVEL = "não reexecutável: {!r} — {}"
ACUSA_EXIT_DIFERENTE_DE_ZERO = ("comando re-executado falhou (exit {}): {!r} "
                                "— prova declarada termina em 0")
ACUSA_SAIDA_DIVERGE = "saída diverge em {!r}: {}"
ACUSA_LINHA_AUSENTE = ("a linha declarada {!r} não aparece na saída "
                       "({} contra {} caracteres)")
ACUSA_ENQUADRAMENTO = (
    "a linha declarada {!r} aparece na saída com outro enquadramento: agora é "
    "{!r}. O conteúdo é o mesmo — o que mudou foi o número de linha, o "
    "caminho ou o recuo que a ferramenta imprime na frente. Isto NÃO é prova "
    "falsa: declare a linha como ela sai hoje, ou corte o prefixo na própria "
    "prova (por exemplo com `-h` no grep, ou `cut -d: -f2-`), e re-execute.")
PREFIXO_DE_FERRAMENTA = re.compile(r"^[^:]{0,120}:\d+:")
NUMERO_NA_FRENTE = re.compile(r"^\s*\d+[:\t ]")
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
ACUSA_CRITERIO_SEM_RESPOSTA = (
    "critério da issue sem resposta nas evidências: {!r} — nada no provado "
    "nem no suposto cita {}")

INSTAVEL_DURACAO = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:s|seg|segs|segundos|ms|min|mins|minutos|"
    r"h|horas)\b", re.IGNORECASE)
INSTAVEL_RELOGIO = re.compile(
    r"\b(?:\d{1,2}:\d{2}(?::\d{2})?|\d{4}-\d{2}-\d{2})\b")
SUBSTANTIVOS_DE_CONTAGEM = (r"casos?|rotinas?|ocorr[eê]ncias?|"
                            r"arquivos?|linhas?")
INSTAVEL_CONTAGEM_VIVA = re.compile(
    r"\b\d+\s+(?:de|of)\s+\d+\b|\b\d+\s+(?:"
    + SUBSTANTIVOS_DE_CONTAGEM + r")\b", re.IGNORECASE)

INSTAVEIS = (
    ("duração", INSTAVEL_DURACAO),
    ("relógio ou data", INSTAVEL_RELOGIO),
    ("contagem de saída viva", INSTAVEL_CONTAGEM_VIVA),
)

AVISO_NUMERO_INSTAVEL = (
    "AVISO [{rotulo}] a saída declarada de {comando!r} carrega {tipo} "
    "({trecho!r}) — número assim muda entre rodadas e a prova para de "
    "reproduzir. Declare a parte estável da saída, ou um comando cuja saída "
    "não dependa do relógio nem do tamanho de hoje.")

CONTAGEM_NA_AFIRMACAO = re.compile(
    r"\b(\d+)\s+(?:" + SUBSTANTIVOS_DE_CONTAGEM + r")\b", re.IGNORECASE)

AVISO_CONTAGEM_SEM_LASTRO = (
    "AVISO [{rotulo}] a afirmação de {comando!r} conta {trecho!r}, e esse "
    "número não aparece na saída declarada — contagem em prosa não é prova. "
    "Confira o número na saída, ou tire a contagem da afirmação.")

AVISO_DO_GREP = (" [aviso: o comando usa `grep` sem caminho — a sessão pode "
                 "ter rodado um embrulhado, que respeita o .gitignore, e esta "
                 "re-execução usou o do PATH. Declare /bin/grep ou git grep]")

LINHA_DO_ENSAIO = "    ensaio: re-executaria {!r} com teto de {}s"
LINHA_IGNORADO = "    ignorado (não tem nome de evidência): {}"
LINHA_ACUSA = "ACUSA {}"
RESUMO_ACUSACOES = "\n{} acusações em {} evidências."
RESUMO_TUDO_BATE = "tudo bate: {} evidências ({}), nenhuma acusação."
RESUMO_CRITERIOS_ACUSADOS = "\n{} de {} critérios abertos sem resposta."
RESUMO_CRITERIOS_COBERTOS = ("todos os {} critérios abertos da issue têm "
                             "resposta em {} evidências.")
RESUMO_SEM_CRITERIO = "a issue não traz critério aberto — nada a verificar."
RESUMO_SEM_CRITERIO_NO_BLOCO = ("o bloco declarado não traz critério aberto — "
                                "nada a verificar.")
MODO_ENSAIO = "ensaio — nada re-executado"
MODO_REEXECUTADO = "re-executado"

ERRO_CWD_INEXISTENTE = "erro de uso: --cwd {} não existe"
ERRO_TEMPO_LIMITE_INVALIDO = ("erro de uso: --tempo-limite {} não é inteiro "
                              ">= 1")
ERRO_EXIGIR_POR_ETAPA = ("erro de uso: --exigir é por etapa — use o modo "
                         "evidência, um arquivo por vez")
ERRO_ALVO_INEXISTENTE = "erro de uso: {} não existe"
ERRO_ALVO_NAO_E_PASTA = "erro de uso: {} não é uma pasta de trabalho"
ERRO_PASTA_SEM_EVIDENCIA = "erro de uso: nenhuma evidência em {}"
ERRO_DE_AMBIENTE = "erro de ambiente: {}"
ERRO_CRITERIOS_ILEGIVEIS = "erro de uso: não li os critérios de {}: {}"
ERRO_BLOCO_FORA_DO_CORPO = ("erro de uso: o bloco {bloco} não existe no corpo "
                            "da issue vindo de {origem}")

AJUDA_MODO_EVIDENCIA = "verifica uma evidência"
AJUDA_MODO_TRABALHO = "verifica todos os *.json de uma pasta"
AJUDA_CWD = "diretório de trabalho da etapa (onde re-executar)"
AJUDA_AMOSTRA = "re-executa só N itens do provado; 0 = todos"
AJUDA_EXIGIR = "termo que o provado precisa citar (do roteiro)"
AJUDA_ENSAIO = "lista o que re-executaria, sem executar nada"
AJUDA_IGUAL = ("exige saída idêntica; o padrão é o declarado aparecer na "
               "saída como bloco de linhas")
AJUDA_TEMPO_LIMITE = ("teto em segundos de cada re-execução; o item do "
                      "provado que declara `tempo-limite` usa o dele")
AJUDA_MODO_CRITERIOS = ("verifica os critérios abertos da issue contra as "
                        "evidências das pastas inteiras — várias pastas da "
                        "mesma issue respondem juntas; a evidência sintética "
                        "da verificação fica fora")
AJUDA_BLOCO = ("cobra só os critérios da seção `## Bloco N` do corpo; sem "
               "ela, cobra a issue inteira")
AJUDA_CRITERIOS = ("de onde vem o corpo da issue: `-` para a entrada padrão, "
                   "ou o caminho de um arquivo")

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


def _sem_espaco_no_fim(linha: str) -> str:
    return linha.rstrip()


def _so_o_conteudo(linha: str) -> str:
    sem_caminho = PREFIXO_DE_FERRAMENTA.sub("", _sem_espaco_no_fim(linha))
    return NUMERO_NA_FRENTE.sub("", sem_caminho).strip()


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
        bloco = [_sem_espaco_no_fim(l) for l in bloco]
        for i in range(inicio, len(linhas) - tamanho + 1):
            if [_sem_espaco_no_fim(l) for l in linhas[i:i + tamanho]] == bloco:
                achou = i
                break
        if achou < 0:
            return False
        inicio = achou + tamanho
    return True


def _verifica_saida(real: str, declarada: str, igual: bool) -> bool:
    if igual or not declarada:
        return ([_sem_espaco_no_fim(l) for l in real.split("\n")]
                == [_sem_espaco_no_fim(l) for l in declarada.split("\n")])
    return _contem_blocos(real, declarada)


def _linha_que_falta(declarada: str, real: str) -> str:
    reais = real.split("\n")
    presentes = {_sem_espaco_no_fim(l) for l in reais}
    por_conteudo = {_so_o_conteudo(l): l for l in reais if _so_o_conteudo(l)}
    for bloco in _blocos_declarados(declarada):
        for linha in bloco:
            if _sem_espaco_no_fim(linha) in presentes:
                continue
            parecida = por_conteudo.get(_so_o_conteudo(linha))
            if parecida is not None:
                return ACUSA_ENQUADRAMENTO.format(linha, parecida)
            return ACUSA_LINHA_AUSENTE.format(linha, len(declarada),
                                              len(real))
    return ACUSA_ORDEM_DAS_LINHAS.format(len(declarada), len(real), ELISAO)


def _o_que_torna_instavel(saida: str):
    for tipo, padrao in INSTAVEIS:
        achado = padrao.search(saida or "")
        if achado:
            return tipo, achado.group(0)
    return "", ""


def avisos_do_numero_instavel(provado: list, rotulo: str) -> list:
    avisos = []
    for item in provado:
        tipo, trecho = _o_que_torna_instavel(item.get("saida", ""))
        if tipo:
            avisos.append(AVISO_NUMERO_INSTAVEL.format(
                rotulo=rotulo, comando=item.get("comando", ""), tipo=tipo,
                trecho=trecho))
    return avisos

def _contagem_sem_lastro(item: dict) -> str:
    saida = item.get("saida") or ""
    afirmacao = item.get("afirmacao") or ""
    for achado in CONTAGEM_NA_AFIRMACAO.finditer(afirmacao):
        if not re.search(r"\b" + achado.group(1) + r"\b", saida):
            return achado.group(0)
    return ""


def avisos_da_contagem_na_afirmacao(provado: list, rotulo: str) -> list:
    avisos = []
    for item in provado:
        trecho = _contagem_sem_lastro(item)
        if trecho:
            avisos.append(AVISO_CONTAGEM_SEM_LASTRO.format(
                rotulo=rotulo, comando=item.get("comando", ""),
                trecho=trecho))
    return avisos


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


def _teto_do_item(item: dict, tempo_limite: int) -> int:
    return item.get(CAMPO_DO_TEMPO_LIMITE) or tempo_limite


def _reexecutar(item: dict, cwd: str, tempo_limite: int,
                igual: bool = False) -> str:
    teto = _teto_do_item(item, tempo_limite)
    try:
        rodada = subprocess.run(item["comando"], shell=True, cwd=cwd,
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=teto,
                                executable=SHELL_DA_REEXECUCAO)
    except subprocess.TimeoutExpired:
        return ACUSA_TEMPO_ESGOTADO.format(teto=teto, comando=item["comando"],
                                           campo=CAMPO_DO_TEMPO_LIMITE)
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
    semente = json.dumps(dado, sort_keys=True, ensure_ascii=False)
    return random.Random(semente).sample(provado, quantos)


def _acusacoes_da_reexecucao(itens: list, cwd: str, tempo_limite: int,
                             igual: bool, ensaio: bool, rotulo: str) -> list:
    acusacoes = []
    for item in itens:
        if ensaio:
            print(LINHA_DO_ENSAIO.format(item["comando"],
                                         _teto_do_item(item, tempo_limite)))
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
    for aviso in avisos_do_numero_instavel(provado, rotulo):
        print(aviso)
    for aviso in avisos_da_contagem_na_afirmacao(provado, rotulo):
        print(aviso)
    acusacoes += _acusacoes_das_exigencias(provado, exigencias, rotulo)
    acusacoes += _acusacoes_do_proximo(dado.get("proximo", ""), rotulo)
    acusacoes += _acusacoes_da_pergunta(dado.get("pergunta", ""), rotulo)
    return acusacoes


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto.lower())
    return "".join(letra for letra in decomposto
                   if unicodedata.category(letra) != "Mn")


def termos_distintivos(texto: str) -> set:
    palavras = FORA_DO_TERMO.split(_sem_acento(texto))
    return {palavra for palavra in palavras
            if len(palavra) >= TAMANHO_MINIMO_DO_TERMO
            and palavra not in BANAIS}


def criterios_abertos(corpo: str) -> list:
    return CRITERIO_ABERTO.findall(corpo)


def criterios_por_bloco(corpo: str) -> dict:
    por_bloco, atual = {}, None
    for linha in corpo.splitlines():
        if CABECALHO_DE_SECAO.match(linha):
            de_um_bloco = SECAO_DE_UM_BLOCO.match(linha)
            atual = de_um_bloco.group(1) if de_um_bloco else None
            if atual is not None:
                por_bloco.setdefault(atual, [])
        elif atual is not None and (achado :=
                                       CRITERIO_ABERTO.match(linha)):
            por_bloco[atual].append(achado.group(1))
    return por_bloco


def _criterios_no_escopo(corpo: str, bloco) -> tuple:
    todos = criterios_abertos(corpo)
    if not bloco:
        return todos, False
    por_bloco = criterios_por_bloco(corpo)
    if str(bloco) not in por_bloco:
        return None, True
    do_bloco = por_bloco[str(bloco)]
    return do_bloco, True


def _declarado_nas_evidencias(arquivos: list) -> tuple:
    declarado, acusacoes = set(), []
    for arquivo in arquivos:
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError) as erro:
            acusacoes.append(ROTULADA.format(
                arquivo.name, ACUSA_EVIDENCIA_ILEGIVEL.format(erro)))
            continue
        if not isinstance(dado, dict):
            acusacoes.append(ROTULADA.format(
                arquivo.name, ACUSA_EVIDENCIA_ILEGIVEL.format(NAO_E_OBJETO)))
            continue
        for item in dado.get("provado") or []:
            if isinstance(item, dict):
                declarado |= termos_distintivos(" ".join(
                    str(item.get(campo, "")) for campo in CAMPOS_DA_PROVA))
        for campo in CAMPOS_QUE_RESPONDEM:
            for item in dado.get(campo) or []:
                declarado |= termos_distintivos(str(item))
    return declarado, acusacoes


def acusacoes_dos_criterios(criterios: list, declarado: set) -> list:
    acusacoes = []
    for criterio in criterios:
        procurados = termos_distintivos(criterio)
        faltando = sorted(procurados - declarado)
        if procurados and len(faltando) * 2 > len(procurados):
            acusacoes.append(ACUSA_CRITERIO_SEM_RESPOSTA.format(
                criterio[:LIMITE_DO_CRITERIO],
                ", ".join(faltando[:LIMITE_DOS_TERMOS])))
    return acusacoes


def _corpo_da_issue(de_onde: str) -> str:
    if de_onde == ENTRADA_PADRAO:
        return sys.stdin.read()
    return Path(de_onde).read_text(encoding="utf-8")


def respondem_ao_criterio(arquivos: list) -> list:
    return [arquivo for arquivo in arquivos
            if not NOME_DA_VERIFICACAO.fullmatch(arquivo.name)]


def verificar_criterios(alvos: list, de_onde: str, bloco=None) -> int:
    for alvo in alvos:
        if not alvo.is_dir():
            print(ERRO_ALVO_NAO_E_PASTA.format(alvo), file=sys.stderr)
            return 2
    try:
        corpo = _corpo_da_issue(de_onde)
    except (OSError, UnicodeDecodeError) as erro:
        print(ERRO_CRITERIOS_ILEGIVEIS.format(de_onde, erro), file=sys.stderr)
        return 2
    criterios, do_escopo = _criterios_no_escopo(corpo, bloco)
    if criterios is None:
        print(ERRO_BLOCO_FORA_DO_CORPO.format(bloco=bloco, origem=de_onde),
              file=sys.stderr)
        return 2
    if not criterios:
        print(RESUMO_SEM_CRITERIO_NO_BLOCO if do_escopo
              else RESUMO_SEM_CRITERIO)
        return 0
    arquivos = [a for alvo in alvos for a in _evidencias_da_pasta(alvo)]
    if not arquivos:
        print(ERRO_PASTA_SEM_EVIDENCIA.format(
            ", ".join(str(alvo) for alvo in alvos)), file=sys.stderr)
        return 2
    respondentes = respondem_ao_criterio(arquivos)
    declarado, acusacoes = _declarado_nas_evidencias(respondentes)
    acusacoes += acusacoes_dos_criterios(criterios, declarado)
    for acusacao in acusacoes:
        print(LINHA_ACUSA.format(acusacao))
    if acusacoes:
        print(RESUMO_CRITERIOS_ACUSADOS.format(len(acusacoes), len(criterios)))
        return 4
    print(RESUMO_CRITERIOS_COBERTOS.format(len(criterios),
                                          len(respondentes)))
    return 0


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
                       default=TEMPO_LIMITE_PADRAO, help=AJUDA_TEMPO_LIMITE)

    comuns(sub.add_parser("evidencia", help=AJUDA_MODO_EVIDENCIA))
    comuns(sub.add_parser("trabalho", help=AJUDA_MODO_TRABALHO))

    criterios = sub.add_parser("criterios", help=AJUDA_MODO_CRITERIOS)
    criterios.add_argument("alvo", nargs="+")
    criterios.add_argument("--criterios", required=True, help=AJUDA_CRITERIOS)
    criterios.add_argument("--bloco", help=AJUDA_BLOCO)
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
    if args.comando == "criterios":
        return verificar_criterios([Path(a) for a in args.alvo],
                                   args.criterios, args.bloco)
    if args.tempo_limite < 1:
        print(ERRO_TEMPO_LIMITE_INVALIDO.format(args.tempo_limite),
              file=sys.stderr)
        return 2
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
    ("contagem sem lastro na afirmação avisa, não acusa", _base(provado=[
        {"afirmacao": "eram 51 casos no piso", "comando": "echo 59",
         "saida": "59"}]), []),
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


def _cli(argumentos, entrada=None):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())] + argumentos,
        input=entrada, capture_output=True, text=True, timeout=120)


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
         resposta.returncode == 4
         and "tempo esgotado em 1s" in resposta.stdout)
    caso("a acusação de tempo esgotado não se confunde com divergência",
         "saída diverge" not in resposta.stdout
         and "não reexecutável" not in resposta.stdout)
    caso("e ela ensina a linha copiável que declara mais tempo",
         '"tempo-limite": <segundos>' in resposta.stdout)
    resposta = _cli(["trabalho", str(Path(pasta) / "nao-existe")])
    caso("pasta inexistente é erro de uso (exit 2)", resposta.returncode == 2)


def _a_prova_declara_o_proprio_teto(pasta, caso):
    lenta = _gravar(pasta, "teto-da-prova/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "a prova lenta termina e imprime pronto",
         "comando": "sleep 3 && echo pronto", "saida": "pronto",
         "tempo-limite": 30}]))
    caso("prova lenta com o teto declarado passa, mesmo com o teto de fora "
         "menor", _cli(["evidencia", str(lenta), "--tempo-limite",
                        "1"]).returncode == 0)
    resposta = _cli(["evidencia", str(lenta), "--ensaio", "--tempo-limite",
                     "1"])
    caso("o ensaio imprime o tempo-limite efetivo da prova, não o de fora",
         "com teto de 30s" in resposta.stdout)

    estoura = _gravar(pasta, "teto-da-prova/02-fantoche-c1.json", _base(
        provado=[{"afirmacao": "dorme mais que o teto declarado",
                  "comando": "sleep 5", "saida": "", "tempo-limite": 1}]))
    resposta = _cli(["evidencia", str(estoura)])
    caso("prova que estoura o teto declarado ainda acusa, e pelo teto dela",
         resposta.returncode == 4
         and "tempo esgotado em 1s" in resposta.stdout)

    silencio = _gravar(pasta, "teto-da-prova/03-fantoche-c1.json", _base())
    resposta = _cli(["evidencia", str(silencio), "--ensaio"])
    caso("sem declaração nenhuma o teto continua sendo o de 60s de hoje",
         "com teto de 60s" in resposta.stdout)


def _o_teto_declarado_invalido_morre_com_erro_de_uso(pasta, caso):
    honesta = _gravar(pasta, "teto-invalido/01-fantoche-c1.json", _base())
    for valor in ("0", "-5", "nao-e-inteiro"):
        resposta = _cli(["evidencia", str(honesta), "--tempo-limite", valor])
        caso(f"--tempo-limite {valor} morre com erro de uso, nunca em "
             "silêncio", resposta.returncode == 2 and bool(resposta.stderr))

    for valor in (0, -5, "300"):
        torta = _gravar(pasta, "teto-invalido/02-fantoche-c1.json", _base(
            provado=[{"afirmacao": "dorme", "comando": "sleep 1",
                      "saida": "", "tempo-limite": valor}]))
        resposta = _cli(["evidencia", str(torta)])
        caso(f"teto {valor!r} declarado na prova é acusado fora do contrato, "
             "nunca em silêncio",
             resposta.returncode == 4
             and "fora do contrato" in resposta.stdout)


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


def _a_semente_da_amostra_vem_do_texto(caso):
    provado = [{"afirmacao": str(n), "comando": "echo", "saida": ""}
               for n in range(20)]
    dado = _base(trabalho="issue-um")
    caso("mesma entrada, mesma amostra em duas chamadas separadas",
         _amostra_deterministica(dado, provado, 5)
         == _amostra_deterministica(dado, provado, 5))
    caso("entrada diferente, amostra diferente",
         _amostra_deterministica(dado, provado, 5)
         != _amostra_deterministica(_base(trabalho="issue-dois"), provado, 5))


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


def _o_espaco_no_fim_nao_reprova(caso):
    caso("espaço no fim da saída real não reprova",
         _contem_blocos("a linha   \nb", "a linha"))
    caso("espaço no fim da declarada não reprova",
         _contem_blocos("a linha\nb", "a linha   "))
    caso("espaço no fim não reprova nem sob --igual",
         _verifica_saida("a\nb  ", "a  \nb", True))
    caso("conteúdo diferente segue reprovando sob --igual",
         not _verifica_saida("a\nb", "a\nc", True))
    caso("linha genuinamente ausente segue reprovando",
         not _contem_blocos("a\nb", "z"))


def _o_enquadramento_e_distinguido_do_conteudo(caso):
    numerada = _linha_que_falta('2206:    "pela via 4"',
                                '2207:    "pela via 4"')
    caso("número de linha diferente vira acusação de enquadramento",
         "enquadramento" in numerada and "NÃO é prova falsa" in numerada)
    caminho = _linha_que_falta('camada.py:12: achou',
                               'outro.py:99: achou')
    caso("caminho e número na frente também são enquadramento",
         "enquadramento" in caminho)
    sumida = _linha_que_falta("nunca existiu", "outra coisa\nqualquer")
    caso("linha que não existe em lugar nenhum não vira enquadramento",
         "enquadramento" not in sumida and "não aparece" in sumida)
    caso("conteúdo diferente com mesmo número não é enquadramento",
         "enquadramento" not in _linha_que_falta("12: um", "12: outro"))


def _o_bashismo_bate_no_bash(pasta, caso):
    if not SHELL_DA_REEXECUCAO:
        return
    bashista = _gravar(pasta, "bash/01-fantoche-c1.json", _base(provado=[
        {"afirmacao": "o teste composto do bash roda",
         "comando": "[[ 1 -eq 1 ]] && echo ok", "saida": "ok"}]))
    resposta = _cli(["evidencia", str(bashista)])
    caso("bashismo honesto bate no bash", resposta.returncode == 0)


ISSUE_DE_MENTIRA = """# a issue de mentira

## Critérios de pronto

- [x] a paginação da listagem responde em duas páginas
- [ ] o relatório mensal soma os lançamentos estornados
- [ ] o disparo grava o carimbo de tempo da última escrita
"""


def _o_numero_instavel_e_avisado(caso):
    instaveis = [
        ("duração", "4 de 6 rotinas passaram, em 157s"),
        ("relógio", "terminou às 14:07:33"),
        ("data", "medido em 2026-08-22"),
        ("contagem viva", "OK: 194 casos"),
    ]
    for rotulo, saida in instaveis:
        provado = [{"afirmacao": "a", "comando": "true", "saida": saida}]
        caso(f"a saída com {rotulo} vira aviso",
             bool(avisos_do_numero_instavel(provado, "x")))

    estaveis = ["ola", "sem conflito", "", "abc123def", "v0.276"]
    for saida in estaveis:
        provado = [{"afirmacao": "a", "comando": "true", "saida": saida}]
        caso(f"a saída estável {saida!r} não vira aviso",
             not avisos_do_numero_instavel(provado, "x"))

    provado = [{"afirmacao": "a", "comando": "rodar", "saida": "em 42s"}]
    avisos = avisos_do_numero_instavel(provado, "07-x-c1.json")
    aviso = avisos[0] if avisos else ""
    caso("o aviso nomeia a evidência, o comando e o trecho instável",
         "07-x-c1.json" in aviso and "rodar" in aviso and "42s" in aviso)


def _a_contagem_da_afirmacao_e_avisada(caso):
    ausente = [{"afirmacao": "eram 51 casos no piso", "comando": "rodar",
                "saida": "OK: 59 casos"}]
    avisos = avisos_da_contagem_na_afirmacao(ausente, "07-x-c1.json")
    aviso = avisos[0] if avisos else ""
    caso("a contagem da afirmação ausente da saída vira aviso que nomeia "
         "a evidência, o comando e o trecho",
         "07-x-c1.json" in aviso and "rodar" in aviso and "51 casos" in aviso)

    presente = [{"afirmacao": "eram 59 casos no piso", "comando": "rodar",
                 "saida": "OK: 59 casos"}]
    caso("a contagem que aparece na saída não vira aviso",
         not avisos_da_contagem_na_afirmacao(presente, "x"))

    referencias = ["a issue 41 fechou", "o passo 3 rodou",
                   "medido em 2026-08-22", "a linha 12 do arquivo"]
    for afirmacao in referencias:
        provado = [{"afirmacao": afirmacao, "comando": "true", "saida": "ok"}]
        caso(f"o número-referência de {afirmacao!r} não vira aviso",
             not avisos_da_contagem_na_afirmacao(provado, "x"))


def _os_criterios_da_issue_sao_verificados(pasta, caso):
    coberto = {"afirmacao": "o relatorio mensal soma os lancamentos "
                            "estornados", "comando": "echo relatorio",
               "saida": "relatorio"}
    carimbo = {"afirmacao": "o disparo grava o carimbo de tempo da ultima "
                            "escrita", "comando": "echo carimbo",
               "saida": "carimbo"}
    _gravar(pasta, "criterios-cobertos/01-fantoche-c1.json",
            _base(provado=[coberto]))
    _gravar(pasta, "criterios-cobertos/02-fantoche-c1.json",
            _base(provado=[carimbo]))
    resposta = _cli(["criterios", str(Path(pasta) / "criterios-cobertos"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("critério respondido pelo provado de qualquer evidência da pasta "
         "passa com exit 0", resposta.returncode == 0)

    _gravar(pasta, "criterios-a-descoberto/01-fantoche-c1.json",
            _base(provado=[coberto]))
    resposta = _cli(["criterios", str(Path(pasta) / "criterios-a-descoberto"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("critério que nenhuma evidência cita é acusado, com exit 4",
         resposta.returncode == 4)
    caso("e o acusado aparece NOMEADO, não somado",
         "carimbo de tempo" in resposta.stdout
         and "relatório mensal" not in resposta.stdout)
    caso("a acusação nomeia os termos que faltaram",
         "carimbo" in resposta.stdout and "disparo" in resposta.stdout)
    caso("critério já marcado com [x] não é cobrado",
         "paginação" not in resposta.stdout)

    _gravar(pasta, "criterios-confessados/01-fantoche-c1.json",
            _base(provado=[coberto], faltas=["o disparo ainda não grava o "
                                             "carimbo de tempo da última "
                                             "escrita"]))
    resposta = _cli(["criterios", str(Path(pasta) / "criterios-confessados"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("critério confessado em faltas NÃO conta como respondido — a "
         "acusação de ontem cobriria o critério de hoje",
         resposta.returncode == 4)

    _gravar(pasta, "vizinha-a/01-fantoche-c1.json", _base(provado=[coberto]))
    _gravar(pasta, "vizinha-b/01-fantoche-c1.json", _base(provado=[carimbo]))
    resposta = _cli(["criterios", str(Path(pasta) / "vizinha-a"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("a pasta vizinha sozinha acusa o critério que a outra metade prova",
         resposta.returncode == 4)
    resposta = _cli(["criterios", str(Path(pasta) / "vizinha-a"),
                     str(Path(pasta) / "vizinha-b"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("as duas pastas vizinhas juntas fecham os critérios que separadas "
         "acusam", resposta.returncode == 0)
    resposta = _cli(["criterios", str(Path(pasta) / "vizinha-a"),
                     str(Path(pasta) / "nao-existe"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("vizinha declarada que não existe é erro de uso (exit 2), não união "
         "calada", resposta.returncode == 2)

    _gravar(pasta, "com-a-sintetica/01-fantoche-c1.json",
            _base(provado=[coberto]))
    _gravar(pasta, "com-a-sintetica/02-verificacao-c1.json",
            _base(etapa="verificacao", provado=[carimbo]))
    resposta = _cli(["criterios", str(Path(pasta) / "com-a-sintetica"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("a evidência sintética da verificação não responde critério: o que "
         "só ela cita segue acusado", resposta.returncode == 4)

    resposta = _cli(["criterios", str(Path(pasta) / "criterios-cobertos"),
                     "--criterios", "-"], entrada="issue sem caixa nenhuma")
    caso("issue sem critério aberto passa e diz que não havia o que verificar",
         resposta.returncode == 0 and "não traz critério" in resposta.stdout)

    arquivo = Path(pasta) / "corpo-da-issue.md"
    arquivo.write_text(ISSUE_DE_MENTIRA, encoding="utf-8")
    resposta = _cli(["criterios", str(Path(pasta) / "criterios-a-descoberto"),
                     "--criterios", str(arquivo)])
    caso("o corpo da issue também vem de arquivo, não só da entrada padrão",
         resposta.returncode == 4 and "carimbo de tempo" in resposta.stdout)
    resposta = _cli(["criterios", str(Path(pasta) / "nao-existe"),
                     "--criterios", "-"], entrada=ISSUE_DE_MENTIRA)
    caso("pasta inexistente é erro de uso (exit 2), não critério coberto",
         resposta.returncode == 2)


ISSUE_EM_BLOCOS = """# a issue em blocos

## Bloco 3 — o relatório

- [ ] o relatório mensal soma os lançamentos estornados

### a subseção que não encerra o bloco

- [ ] o disparo grava o carimbo de tempo da última escrita

## Ponto de retomada

- [ ] a fila de espera drena antes do desligamento

## Bloco 4 — a paginação

- [x] a paginação da listagem responde em duas páginas
"""


def _o_escopo_do_bloco_recorta_a_cobranca(pasta, caso):
    corpo = Path(pasta) / "issue-em-blocos.md"
    corpo.write_text(ISSUE_EM_BLOCOS, encoding="utf-8")
    relatorio = {"afirmacao": "o relatorio mensal soma os lancamentos "
                              "estornados", "comando": "echo relatorio",
                 "saida": "relatorio"}
    carimbo = {"afirmacao": "o disparo grava o carimbo de tempo da ultima "
                            "escrita", "comando": "echo carimbo",
               "saida": "carimbo"}
    _gravar(pasta, "bloco-3-inteiro/01-fantoche-c1.json",
            _base(provado=[relatorio, carimbo]))
    _gravar(pasta, "so-o-relatorio/01-fantoche-c1.json",
            _base(provado=[relatorio]))

    def _cobrar(alvo, *bandeiras):
        return _cli(["criterios", str(Path(pasta) / alvo),
                     "--criterios", str(corpo), *bandeiras])

    caso("com o bloco declarado, o critério de outro bloco não é cobrado",
         _cobrar("bloco-3-inteiro", "--bloco", "3").returncode == 0)
    inteira = _cobrar("bloco-3-inteiro")
    caso("sem bloco declarado, a issue inteira continua cobrada",
         inteira.returncode == 4 and "fila de espera" in inteira.stdout)

    meio = _cobrar("so-o-relatorio", "--bloco", "3")
    caso("o subtítulo ### não encerra a seção do bloco: o critério abaixo "
         "dele segue cobrado",
         meio.returncode == 4 and "carimbo de tempo" in meio.stdout)
    caso("cabeçalho ## que não é bloco zera o bloco atual: o critério do "
         "Ponto de retomada não é do bloco anterior",
         "fila de espera" not in meio.stdout)

    marcado = _cobrar("so-o-relatorio", "--bloco", "4")
    caso("bloco que existe com todas as caixas marcadas passa com exit 0, "
         "nunca erro de uso",
         marcado.returncode == 0 and "nada a verificar" in marcado.stdout)

    fantasma = _cobrar("so-o-relatorio", "--bloco", "9")
    caso("bloco declarado que o corpo não tem é erro de uso (exit 2), e o "
         "erro nomeia o bloco e a origem do corpo",
         fantasma.returncode == 2 and "bloco 9" in fantasma.stderr
         and str(corpo) in fantasma.stderr)


def _comportamento(pasta):
    resultados = []

    def caso(rotulo, condicao):
        resultados.append((rotulo, bool(condicao)))

    _a_forja_e_acusada_com_exit_4(pasta, caso)
    _o_ensaio_nao_executa_nada(pasta, caso)
    _o_trabalho_inteiro_nomeia_o_forjado(pasta, caso)
    _comando_lento_acusa_por_tempo(pasta, caso)
    _a_prova_declara_o_proprio_teto(pasta, caso)
    _o_teto_declarado_invalido_morre_com_erro_de_uso(pasta, caso)
    _o_lixo_ilegivel_nao_cala_os_vizinhos(pasta, caso)
    _a_amostra_e_deterministica(pasta, caso)
    _a_semente_da_amostra_vem_do_texto(caso)
    _as_fronteiras_de_uso(pasta, caso)
    _o_fifo_nao_pendura_nem_cala(pasta, caso)
    _a_acusacao_aponta_onde_diverge(caso)
    _nome_fora_do_padrao_aparece_como_ignorado(pasta, caso)
    _igual_restaura_a_igualdade_estrita(pasta, caso)
    _o_aviso_do_grep_so_onde_cabe(pasta, caso)
    _a_regua_do_contem(caso)
    _o_espaco_no_fim_nao_reprova(caso)
    _o_enquadramento_e_distinguido_do_conteudo(caso)
    _o_bashismo_bate_no_bash(pasta, caso)
    _o_numero_instavel_e_avisado(caso)
    _a_contagem_da_afirmacao_e_avisada(caso)
    _os_criterios_da_issue_sao_verificados(pasta, caso)
    _o_escopo_do_bloco_recorta_a_cobranca(pasta, caso)
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
