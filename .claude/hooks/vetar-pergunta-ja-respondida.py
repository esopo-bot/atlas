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
DECISAO_DE_PERGUNTAR = "ask"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_SEM_QUEM_RESPONDA = "bypassPermissions"

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


def raiz_do_projeto() -> Path:
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
    }}, ensure_ascii=False))
    return SILENCIO


def verbo_do_veto(entrada: dict) -> str:
    sem_quem_responda = (entrada or {}).get(
        CAMPO_DO_MODO_DE_PERMISSAO) == MODO_SEM_QUEM_RESPONDA
    return DECISAO_DE_NEGAR if sem_quem_responda else DECISAO_DE_PERGUNTAR


def vetar(entrada: dict, razao: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": verbo_do_veto(entrada),
        "permissionDecisionReason": razao,
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto()
    acao = acao_ja_autorizada(texto_das_perguntas(entrada), autorizacoes(raiz))
    if not acao:
        return SILENCIO

    return vetar(entrada, RECUSA.format(acao=acao, arquivo=ARQUIVO_CONFIGURACAO)
                 + MANDA_GRAVAR.format(APRENDIZADO))


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
SEM_CABECA = {CAMPO_DO_MODO_DE_PERMISSAO: MODO_SEM_QUEM_RESPONDA}
PEDIDO_SEM_MODO_DECLARADO = {}


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

    interativa = resposta_do_veto(SESSAO_INTERATIVA, RAZAO_DO_TESTE)
    sem_cabeca = resposta_do_veto(SEM_CABECA, RAZAO_DO_TESTE)
    sem_modo = resposta_do_veto(PEDIDO_SEM_MODO_DECLARADO, RAZAO_DO_TESTE)
    if interativa.get("permissionDecision") != DECISAO_DE_PERGUNTAR:
        falhas.append(TESTE_COMPORTAMENTO.format(
            "em sessão interativa a resposta do gancho traz `ask`: o veto "
            "pergunta antes, em vez de negar de vez"))
    if sem_cabeca.get("permissionDecision") != DECISAO_DE_NEGAR:
        falhas.append(TESTE_COMPORTAMENTO.format(
            "em execução sem cabeça (`--dangerously-skip-permissions`) não "
            "há quem responda: a resposta continua `deny`"))
    if sem_modo.get("permissionDecision") != DECISAO_DE_PERGUNTAR:
        falhas.append(TESTE_COMPORTAMENTO.format(
            "pedido que não declara o modo de permissão recebe `ask` — só "
            "o modo sem cabeça nega"))
    if not (interativa.get("permissionDecisionReason") == RAZAO_DO_TESTE
            and sem_cabeca.get("permissionDecisionReason") == RAZAO_DO_TESTE):
        falhas.append(TESTE_COMPORTAMENTO.format(
            "a razão do veto viaja na resposta, com `ask` e com `deny`: é "
            "ela que o prompt de permissão mostra ao dono"))

    total = len(BARRA) + len(DEIXA_PASSAR) + 8
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR)))
    return 0


def resposta_do_veto(entrada: dict, razao: str) -> dict:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        vetar(entrada, razao)
    try:
        return json.loads(saida.getvalue())["hookSpecificOutput"]
    except (ValueError, KeyError):
        return {}


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
