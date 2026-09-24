import json
import os
import re
import sys
from pathlib import Path

ARQUIVO_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DAS_AUTORIZACOES = "autorizacoes"
VARIAVEL_DA_RAIZ = "CLAUDE_PROJECT_DIR"
BANDEIRA_DE_TESTE = "--testar"

SILENCIO = 0
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)
MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO = (
    "permissão já declarada em `autorizacoes` não se pergunta de novo: "
    "o caminho é fazer a ação."
)

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO = "bypassPermissions"
MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"

ACOES = {
    "push": (r"\bpush(?:es|ar|ei)?\b", r"\bempurr\w+"),
    "commit": (r"\bcommit\w*\b", r"\bcomit\w+"),
    "publicar": (r"\bpublic\w+", r"\bpublicar\b"),
}

PEDE_PERMISSAO = re.compile(
    r"\b(?:posso|pode|podemos|deixa|autoriz\w+|permit\w+|libero|libera|"
    r"fa[cç]o|quer\s+que\s+eu|te[nh]?o\s+que\s+pedir|me\s+autoriza)\b")

NA_PRIMEIRA_PESSOA = re.compile(
    r"\b(?:empurro|commito|comito|publico|mesclo|subo)\b")

ESCOLHA_ENTRE_ALTERNATIVAS = re.compile(r"\s+ou\s+")

RECUSA = (
    "Esta pergunta já está respondida: `autorizacoes.{acao}` está ligado em "
    "{arquivo}. Regra 9 da camada — o que a automação faz sozinha se declara, "
    "e o que está declarado não se pergunta de novo. Pedir permissão que já "
    "se tem gasta o tempo do dono e desgasta a confiança na regra escrita.\n"
    "Faça a ação. Se ela for recusada por outro motivo, o gancho que a recusa "
    "dirá qual.")

AJUDA_SEM_PERGUNTA = "sem pergunta no tool_input"

TESTE_DEVIA_BARRAR = "  DEVIA BARRAR e passou — {}"
TESTE_DEVIA_PASSAR = "  DEVIA PASSAR e barrou — {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
TESTE_COMPORTAMENTO = "  COMPORTAMENTO — {}"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados"


def raiz_da_camada() -> Path:
    posta = os.environ.get(VARIAVEL_DA_RAIZ)
    if posta and (Path(posta) / ARQUIVO_CONFIGURACAO).is_file():
        return Path(posta)
    atual = Path(__file__).resolve().parent
    while True:
        if (atual / ARQUIVO_CONFIGURACAO).is_file():
            return atual
        if atual.parent == atual:
            return Path.cwd()
        atual = atual.parent


def autorizacoes(raiz: Path) -> dict:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    declarado = dado.get(CHAVE_DAS_AUTORIZACOES) if isinstance(dado, dict) \
        else None
    if not isinstance(declarado, dict):
        return {}
    return {acao: valor for acao, valor in declarado.items()
            if isinstance(valor, bool)}


def texto_das_perguntas(entrada: dict) -> str:
    perguntas = (entrada.get("tool_input") or {}).get("questions") or []
    if not isinstance(perguntas, list):
        return ""
    pedacos = []
    for uma in perguntas:
        if not isinstance(uma, dict):
            continue
        pedacos.append(str(uma.get("question", "")))
        pedacos.append(str(uma.get("header", "")))
    return " ".join(pedacos).lower()


def pede_permissao(texto: str) -> bool:
    if ESCOLHA_ENTRE_ALTERNATIVAS.search(texto):
        return False
    return bool(PEDE_PERMISSAO.search(texto)
                or NA_PRIMEIRA_PESSOA.search(texto))


def acao_ja_autorizada(texto: str, permitido: dict) -> str:
    if not texto or not pede_permissao(texto):
        return ""
    for acao, padroes in ACOES.items():
        if not permitido.get(acao):
            continue
        if any(re.search(padrao, texto) for padrao in padroes):
            return acao
    return ""


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}))
    return SILENCIO


AVISO_QUE_NAO_SEGURA_A_PERGUNTA = (
    "AVISO, não veto: a pergunta segue para o dono. Confira se ela não pede "
    "o que o repositório já autorizou.\n\n")


def e_etapa_sem_ninguem(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_DE_ETAPA_NO_AMBIENTE))


def avisar_ou_negar(razao: str, ambiente) -> int:
    if not e_etapa_sem_ninguem(ambiente):
        print(json.dumps(
            {"systemMessage": AVISO_QUE_NAO_SEGURA_A_PERGUNTA + razao}))
        return SILENCIO
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": razao,
    }}))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_da_camada()
    acao = acao_ja_autorizada(texto_das_perguntas(entrada), autorizacoes(raiz))
    if not acao:
        return SILENCIO

    return avisar_ou_negar(RECUSA.format(acao=acao, arquivo=ARQUIVO_CONFIGURACAO)
                           + MANDA_GRAVAR.format(APRENDIZADO), os.environ)


TUDO_LIGADO = {"commit": True, "push": True, "publicar": True}
SO_COMMIT = {"commit": True, "push": False, "publicar": False}

BARRA = [
    ("posso empurrar a branch?", TUDO_LIGADO),
    ("Faço o push da branch de trabalho?", TUDO_LIGADO),
    ("quer que eu commite o que fiz?", TUDO_LIGADO),
    ("me autoriza a publicar?", TUDO_LIGADO),
    ("posso commitar isto?", SO_COMMIT),
    ("empurro a branch `issue/32-x` para o github?", TUDO_LIGADO),
    ("commito o que fiz na branch de trabalho?", TUDO_LIGADO),
]

DEIXA_PASSAR = [
    ("posso empurrar a branch?", SO_COMMIT),
    ("me autoriza a publicar?", SO_COMMIT),
    ("qual mensagem de commit você prefere?", TUDO_LIGADO),
    ("empurro para homolog ou para main?", {}),
    ("posso apagar a pasta de evidências?", TUDO_LIGADO),
    ("qual das duas abordagens você quer?", TUDO_LIGADO),
    ("", TUDO_LIGADO),
]


RAZAO_DO_TESTE = "a razão que o veto explicaria"
MODO_DA_SESSAO_INTERATIVA = "default"
SESSAO_INTERATIVA = {CAMPO_DO_MODO_DE_PERMISSAO: MODO_DA_SESSAO_INTERATIVA}
SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA = {
    CAMPO_DO_MODO_DE_PERMISSAO: MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO}
PEDIDO_SEM_MODO_DECLARADO = {}
AMBIENTE_SEM_A_MARCA = {}
AMBIENTE_DA_ETAPA_SEM_NINGUEM = {MARCA_DE_ETAPA_NO_AMBIENTE: "1"}
PERGUNTA_JA_RESPONDIDA = {"questions": [
    {"question": "Posso commitar o que fiz?", "header": "Commit"}]}
RAZAO_DA_PERGUNTA_JA_RESPONDIDA = "`autorizacoes.commit`"


def testar() -> int:
    falhas = []
    for texto, permitido in BARRA:
        if not acao_ja_autorizada(texto.lower(), permitido):
            falhas.append(TESTE_DEVIA_BARRAR.format(texto))
    for texto, permitido in DEIXA_PASSAR:
        if acao_ja_autorizada(texto.lower(), permitido):
            falhas.append(TESTE_DEVIA_PASSAR.format(texto))

    if texto_das_perguntas({"tool_input": {"questions": [
            {"question": "Posso empurrar?", "header": "Push"}]}}) \
            != "posso empurrar? push":
        falhas.append(TESTE_DEVIA_PASSAR.format("leitura do tool_input"))
    if texto_das_perguntas({}) != "":
        falhas.append(TESTE_DEVIA_PASSAR.format(AJUDA_SEM_PERGUNTA))

    mensagem = (RECUSA.format(acao="push", arquivo=ARQUIVO_CONFIGURACAO)
                + MANDA_GRAVAR.format(APRENDIZADO))
    if "Regra 9" not in mensagem or ARQUIVO_CONFIGURACAO not in mensagem:
        falhas.append(TESTE_DEVIA_BARRAR.format(
            "a recusa nomeia a regra 9 e diz onde o valor certo mora"))
    if "regra 4" not in mensagem or "`conhecimento/`" not in mensagem:
        falhas.append(TESTE_DEVIA_BARRAR.format(
            "a recusa manda gravar o aprendizado em conhecimento/"))

    com_gente = resposta_do_aviso_ou_da_negativa(RAZAO_DO_TESTE,
                                                 AMBIENTE_SEM_A_MARCA)
    sem_ninguem = resposta_do_aviso_ou_da_negativa(
        RAZAO_DO_TESTE, AMBIENTE_DA_ETAPA_SEM_NINGUEM)
    if not ("hookSpecificOutput" not in com_gente
            and RAZAO_DO_TESTE in com_gente.get("systemMessage", "")
            and AVISO_QUE_NAO_SEGURA_A_PERGUNTA
            in com_gente.get("systemMessage", "")):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "sem a marca da etapa há gente: a cerca AVISA e deixa a "
            "pergunta passar — ela lê prosa, erra em exemplo citado, e "
            "pergunta a mais custa menos ao dono que pergunta legítima "
            "recusada"))
    if sem_ninguem.get("hookSpecificOutput", {}).get(
            "permissionDecision") != DECISAO_DE_NEGAR:
        falhas.append(TESTE_COMPORTAMENTO.format(
            "com a marca da etapa no ambiente não há quem responda: a "
            "resposta é `deny`"))
    if sem_ninguem.get("hookSpecificOutput", {}).get(
            "permissionDecisionReason") != RAZAO_DO_TESTE:
        falhas.append(TESTE_COMPORTAMENTO.format(
            "a razão viaja na resposta também quando nega: é ela que o "
            "registro da etapa guarda"))

    def so_avisa(resposta) -> bool:
        aviso = resposta.get("systemMessage", "")
        return ("hookSpecificOutput" not in resposta
                and AVISO_QUE_NAO_SEGURA_A_PERGUNTA in aviso
                and RAZAO_DA_PERGUNTA_JA_RESPONDIDA in aviso)

    if not so_avisa(resposta_do_gancho(
            pedido_da_pergunta(SESSAO_INTERATIVA), AMBIENTE_SEM_A_MARCA)):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "pelo gancho inteiro, em modo `default` sem a marca da etapa: o "
            "dono está, a cerca AVISA e a pergunta segue"))
    if not so_avisa(resposta_do_gancho(
            pedido_da_pergunta(SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA),
            AMBIENTE_SEM_A_MARCA)):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "pelo gancho inteiro, em `bypassPermissions` sem a marca: há "
            "gente, e a pergunta é ela mesma o caminho até o dono — a cerca "
            "AVISA; negar ali barraria pergunta que só citasse commit"))
    if not so_avisa(resposta_do_gancho(
            pedido_da_pergunta(PEDIDO_SEM_MODO_DECLARADO),
            AMBIENTE_SEM_A_MARCA)):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "pelo gancho inteiro, pedido sem o modo declarado e sem a marca: "
            "a cerca AVISA"))
    na_etapa = resposta_do_gancho(pedido_da_pergunta(SESSAO_INTERATIVA),
                                  AMBIENTE_DA_ETAPA_SEM_NINGUEM).get(
                                      "hookSpecificOutput", {})
    if not (na_etapa.get("permissionDecision") == DECISAO_DE_NEGAR
            and RAZAO_DA_PERGUNTA_JA_RESPONDIDA
            in na_etapa.get("permissionDecisionReason", "")):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "pelo gancho inteiro, na etapa do executor, com a marca no "
            "ambiente, ninguém responde nem em modo `default`: a cerca NEGA, "
            "com a razão"))

    total = len(BARRA) + len(DEIXA_PASSAR) + 11
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR)))
    return 0


def resposta_do_aviso_ou_da_negativa(razao: str, ambiente) -> dict:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        avisar_ou_negar(razao, ambiente)
    try:
        return json.loads(saida.getvalue())
    except ValueError:
        return {}


def pedido_da_pergunta(sessao: dict) -> dict:
    return dict(sessao, tool_name="AskUserQuestion",
                tool_input=PERGUNTA_JA_RESPONDIDA)


def resposta_do_gancho(pedido: dict, ambiente: dict) -> dict:
    import contextlib
    import io
    import tempfile
    guardados = {nome: os.environ.pop(nome, None)
                 for nome in (VARIAVEL_DA_RAIZ, MARCA_DE_ETAPA_NO_AMBIENTE)}
    saida = io.StringIO()
    guardada, sys.stdin = sys.stdin, io.StringIO(json.dumps(pedido))
    try:
        with tempfile.TemporaryDirectory(prefix="veto-pergunta-") as tmp:
            configuracao = Path(tmp) / ARQUIVO_CONFIGURACAO
            configuracao.parent.mkdir(parents=True)
            configuracao.write_text(json.dumps(
                {CHAVE_DAS_AUTORIZACOES: TUDO_LIGADO}), encoding="utf-8")
            os.environ[VARIAVEL_DA_RAIZ] = tmp
            os.environ.update(ambiente)
            with contextlib.redirect_stdout(saida):
                decidir()
    finally:
        sys.stdin = guardada
        for nome, valor in guardados.items():
            os.environ.pop(nome, None)
            if valor is not None:
                os.environ[nome] = valor
    try:
        return json.loads(saida.getvalue())
    except ValueError:
        return {}


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
