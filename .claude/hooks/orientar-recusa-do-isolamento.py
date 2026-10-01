import json
import re
import sys
from pathlib import Path

EVENTO_DEPOIS_DA_FALHA = "PostToolUseFailure"
FERRAMENTAS_DE_SHELL = ("Bash", "PowerShell")
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

CHAVE_DA_SAIDA = "hookSpecificOutput"
CHAVE_DO_EVENTO = "hookEventName"
CHAVE_DO_CONTEXTO = "additionalContext"
CHAVE_DA_FERRAMENTA = "tool_name"
CHAVE_DA_ENTRADA_DA_FERRAMENTA = "tool_input"
CHAVE_DO_COMANDO = "command"
CHAVE_DO_ERRO = "error"
CHAVE_DA_INTERRUPCAO = "is_interrupt"

COMECO_DA_RECUSA_NA_SESSAO = "This session is isolated in the worktree "
COMECO_DA_RECUSA_NO_SUBAGENTE = "This agent is isolated in the worktree "
COMECOS_DA_RECUSA_DO_ISOLAMENTO = (COMECO_DA_RECUSA_NA_SESSAO,
                                   COMECO_DA_RECUSA_NO_SUBAGENTE)
FIM_DA_FORMA_COMPLEXA = "too complex to verify"
FIM_DO_REDIRECIONAMENTO = "redirects git to the shared checkout"
SUBCOMANDO_DO_CHECKOUT_PRINCIPAL = re.compile(r"\b(?:merge|commit|switch)\b")

FRASE_DA_FORMA_COMPLEXA = "O isolamento não lê o roteiro"
FRASE_DO_REDIRECIONAMENTO = "As refs são compartilhadas"
FRASE_DA_MESCLA = "em HEAD destacado"
FRASE_DA_GENERICA = "A razão impressa é a receita"

FORMA_COMPLEXA = (
    "O isolamento de worktree recusou este comando antes de rodar: pelo "
    "texto, ele não provou que todo git do comando fica nesta worktree. "
    "Passam: um comando literal por chamada; o nome do programa escrito "
    "(`git`, `python`), nunca numa variável nem montado por `$(...)`; git "
    "fora de `python -c`. Laço e composição cabem num roteiro `.py` na pasta "
    "de rascunho da sessão, chamado pelo caminho por extenso. "
    + FRASE_DA_FORMA_COMPLEXA +
    ": o git dele roda onde o roteiro mandar, então o roteiro não leva `-C`, "
    "`--git-dir` nem `cd` para fora desta worktree. A mesma forma com outra "
    "pontuação é recusada de novo.")
FORMA_DO_REDIRECIONAMENTO = (
    "O isolamento de worktree recusou o redirecionamento do git (`-C`, "
    "`--git-dir`, `GIT_DIR` ou `cd`) para o checkout principal: numa sessão "
    "isolada, o git só age na própria worktree. O mesmo comando sem o "
    "redirecionamento, rodado daqui, passa. "
    + FRASE_DO_REDIRECIONAMENTO +
    ": `git log <integração>` e `git diff <integração>...HEAD` rodam daqui, "
    "com a integração que `nucleo/executor.json` declara em "
    "`branches.integracao`. A árvore de trabalho da raiz não se lê de dentro "
    "do isolamento: `git status` e `git diff` sem ref mostram só esta "
    "worktree.")
RECEITA_DA_MESCLA = (
    " Mesclar na integração se faz nesta worktree, " + FRASE_DA_MESCLA +
    ": `git switch --detach origin/<integração>` e depois "
    "`git merge --no-ff <branch>`; ou fora do isolamento.")
FORMA_GENERICA = (
    "O isolamento de worktree recusou este comando antes de rodar. "
    + FRASE_DA_GENERICA +
    ": um comando literal por chamada, a partir desta worktree.")

NAO_MEDIU = ("orientar-recusa-do-isolamento NÃO MEDIU: {}. Sem a entrada, a "
             "recusa, se houve, ficou sem orientação.")


def comando_da_ferramenta(entrada: dict) -> str:
    dada = entrada.get(CHAVE_DA_ENTRADA_DA_FERRAMENTA)
    comando = dada.get(CHAVE_DO_COMANDO) if isinstance(dada, dict) else ""
    return comando if isinstance(comando, str) else ""


def orientacao(entrada: dict) -> str:
    if entrada.get(CHAVE_DA_FERRAMENTA) not in FERRAMENTAS_DE_SHELL:
        return ""
    if entrada.get(CHAVE_DA_INTERRUPCAO):
        return ""
    erro = entrada.get(CHAVE_DO_ERRO)
    if not isinstance(erro, str):
        return ""
    if not erro.lstrip().startswith(COMECOS_DA_RECUSA_DO_ISOLAMENTO):
        return ""
    if FIM_DA_FORMA_COMPLEXA in erro:
        return FORMA_COMPLEXA
    if FIM_DO_REDIRECIONAMENTO in erro:
        mescla = SUBCOMANDO_DO_CHECKOUT_PRINCIPAL.search(
            comando_da_ferramenta(entrada))
        receita = RECEITA_DA_MESCLA if mescla else ""
        return FORMA_DO_REDIRECIONAMENTO + receita
    return FORMA_GENERICA


def saida_com_o_contexto(texto: str) -> str:
    return json.dumps({CHAVE_DA_SAIDA: {
        CHAVE_DO_EVENTO: EVENTO_DEPOIS_DA_FALHA,
        CHAVE_DO_CONTEXTO: texto}}, ensure_ascii=True)


def main() -> int:
    try:
        entrada = json.loads(sys.stdin.read())
    except ValueError as falha:
        print(NAO_MEDIU.format("%s: %s" % (type(falha).__name__, falha)),
              file=sys.stderr)
        return SILENCIO
    if not isinstance(entrada, dict):
        print(NAO_MEDIU.format("a entrada não é um objeto JSON"),
              file=sys.stderr)
        return SILENCIO
    texto = orientacao(entrada)
    if texto:
        print(saida_com_o_contexto(texto))
    return SILENCIO


WORKTREE_DE_MENTIRA = "/repo/.claude/worktrees/x"
ERRO_DA_FORMA_COMPLEXA = (
    COMECO_DA_RECUSA_NA_SESSAO + WORKTREE_DE_MENTIRA + ", but this "
    "command names git in a form too complex to verify that it stays inside "
    "the worktree. Refusing to run it. Split it into plain, separate "
    "commands and run them from " + WORKTREE_DE_MENTIRA + ".")
ERRO_DO_REDIRECIONAMENTO = (
    COMECO_DA_RECUSA_NA_SESSAO + WORKTREE_DE_MENTIRA + ", but this "
    "command redirects git to the shared checkout via -C. Run it without the "
    "redirect.")
ERRO_DE_FIM_DESCONHECIDO = (
    COMECO_DA_RECUSA_NA_SESSAO + WORKTREE_DE_MENTIRA + ", but this "
    "command frobnicates the index.")
ERRO_DO_CD_CALCULADO_NO_SUBAGENTE = (
    COMECO_DA_RECUSA_NO_SUBAGENTE + WORKTREE_DE_MENTIRA + ", but this "
    "command changes directory to a location computed at runtime before "
    "running git. Refusing to run it — a worktree-isolated agent's git "
    "operations must target its own worktree. Run the equivalent from "
    + WORKTREE_DE_MENTIRA + " without the redirect.")
ERRO_COMUM = "Exit code 1\nfatal: not a git repository"

FRASES_DAS_FORMAS = (FRASE_DA_FORMA_COMPLEXA, FRASE_DO_REDIRECIONAMENTO,
                     FRASE_DA_MESCLA, FRASE_DA_GENERICA)


def entrada_de_mentira(erro, comando="git status", ferramenta="Bash",
                       interrompida=False) -> dict:
    return {"session_id": "sessao-de-mentira", "cwd": WORKTREE_DE_MENTIRA,
            "hook_event_name": EVENTO_DEPOIS_DA_FALHA,
            CHAVE_DA_FERRAMENTA: ferramenta,
            CHAVE_DA_ENTRADA_DA_FERRAMENTA: {CHAVE_DO_COMANDO: comando},
            "tool_use_id": "toolu_de_mentira", CHAVE_DO_ERRO: erro,
            CHAVE_DA_INTERRUPCAO: interrompida, "duration_ms": 80}


BANCADA_DAS_FORMAS = (
    ("VERMELHO — a recusa 'too complex' ganha a forma do roteiro",
     entrada_de_mentira(ERRO_DA_FORMA_COMPLEXA,
                        "G=$(echo git); $G status --short"),
     (FRASE_DA_FORMA_COMPLEXA,)),
    ("a mesma recusa no PowerShell ganha a mesma forma",
     entrada_de_mentira(ERRO_DA_FORMA_COMPLEXA, "$g = 'git'; & $g status",
                        "PowerShell"),
     (FRASE_DA_FORMA_COMPLEXA,)),
    ("a recusa do -C sem mescla ganha as refs compartilhadas, sem a receita "
     "da mescla",
     entrada_de_mentira(ERRO_DO_REDIRECIONAMENTO, "git -C /repo log -1"),
     (FRASE_DO_REDIRECIONAMENTO,)),
    ("a recusa do -C num merge ganha também a mescla em HEAD destacado",
     entrada_de_mentira(ERRO_DO_REDIRECIONAMENTO,
                        "git -C /repo merge --no-ff issue/1-x"),
     (FRASE_DO_REDIRECIONAMENTO, FRASE_DA_MESCLA)),
    ("a recusa do -C num commit ganha a mescla",
     entrada_de_mentira(ERRO_DO_REDIRECIONAMENTO,
                        "git -C /repo commit -m x"),
     (FRASE_DO_REDIRECIONAMENTO, FRASE_DA_MESCLA)),
    ("a recusa do isolamento com fim desconhecido ganha a forma genérica",
     entrada_de_mentira(ERRO_DE_FIM_DESCONHECIDO), (FRASE_DA_GENERICA,)),
    ("VERMELHO — a recusa do subagente, com o cd calculado ao rodar, ganha a "
     "forma genérica",
     entrada_de_mentira(ERRO_DO_CD_CALCULADO_NO_SUBAGENTE,
                        'cd "$(git rev-parse --show-toplevel)" && git status'),
     (FRASE_DA_GENERICA,)),
)

BANCADA_DO_SILENCIO = (
    ("CONTROLE — a falha comum passa calada",
     entrada_de_mentira(ERRO_COMUM)),
    ("CONTROLE — a frase do isolamento no meio da saída passa calada",
     entrada_de_mentira("Exit code 1\n" + ERRO_DA_FORMA_COMPLEXA)),
    ("CONTROLE — a interrupção passa calada",
     entrada_de_mentira(ERRO_DA_FORMA_COMPLEXA, interrompida=True)),
    ("CONTROLE — outra ferramenta passa calada",
     entrada_de_mentira(ERRO_DA_FORMA_COMPLEXA, ferramenta="Read")),
    ("CONTROLE — erro que não é texto passa calado",
     entrada_de_mentira(None)),
)

ENTRADAS_ILEGIVEIS = (
    ("a lista no lugar do objeto", "[1, 2]"),
    ("o texto solto", "isto não é JSON"),
)


def orientar_na_bancada(corpo: str) -> tuple:
    import contextlib
    import io
    saida, erro = io.StringIO(), io.StringIO()
    guardado = sys.stdin
    sys.stdin = io.StringIO(corpo)
    try:
        with contextlib.redirect_stdout(saida), \
                contextlib.redirect_stderr(erro):
            codigo = main()
    finally:
        sys.stdin = guardado
    return codigo, saida.getvalue(), erro.getvalue()


def porta_da_frente_com_cp1252() -> list:
    import os
    import subprocess
    ambiente = {k: v for k, v in os.environ.items()
                if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    ambiente.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
    corpo = json.dumps(entrada_de_mentira(
        ERRO_DA_FORMA_COMPLEXA, "G=$(echo git); $G status")).encode("utf-8")
    corrida = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())], input=corpo,
        env=ambiente, capture_output=True, timeout=60)
    try:
        bloco = json.loads(corrida.stdout.decode("utf-8"))[CHAVE_DA_SAIDA]
    except (UnicodeDecodeError, ValueError, KeyError, TypeError) as falha:
        return ["porta da frente com cp1252: a saída não é JSON em UTF-8 "
                "estrito (%s), saiu %d, erro %r" % (
                    type(falha).__name__, corrida.returncode,
                    corrida.stderr.decode("utf-8", "replace")[-200:])]
    falhas = []
    if corrida.returncode != SILENCIO:
        falhas.append("porta da frente com cp1252: saiu %d"
                      % corrida.returncode)
    if bloco.get(CHAVE_DO_EVENTO) != EVENTO_DEPOIS_DA_FALHA:
        falhas.append("porta da frente com cp1252: o evento saiu %r, e o "
                      "cliente descarta contexto de outro evento"
                      % bloco.get(CHAVE_DO_EVENTO))
    if bloco.get(CHAVE_DO_CONTEXTO) != FORMA_COMPLEXA:
        falhas.append("porta da frente com cp1252: o texto chegou mudado")
    return falhas


def linha_da_orientacao_no_settings() -> list:
    configuracao = Path(__file__).resolve().parents[1] / "settings.json"
    try:
        blocos = json.loads(configuracao.read_text(encoding="utf-8"))[
            "hooks"][EVENTO_DEPOIS_DA_FALHA]
        ligados = [bloco.get("matcher") for bloco in blocos
                   if any(Path(__file__).name in gancho.get("command", "")
                          for gancho in bloco.get("hooks", []))]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as erro:
        return ["a linha do gancho no %s NÃO MEDIU: %s" % (
            configuracao.name, type(erro).__name__)]
    if ligados != ["|".join(FERRAMENTAS_DE_SHELL)]:
        return ["a linha que chama este gancho em %s tem de ser uma só, no "
                "evento %s, com o matcher %s — veio %r" % (
                    configuracao.name, EVENTO_DEPOIS_DA_FALHA,
                    "|".join(FERRAMENTAS_DE_SHELL), ligados)]
    return []


def testar() -> int:
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    for rotulo, entrada, esperadas in BANCADA_DAS_FORMAS:
        codigo, saida, erro = orientar_na_bancada(json.dumps(entrada))
        try:
            bloco = json.loads(saida)[CHAVE_DA_SAIDA]
            texto = bloco[CHAVE_DO_CONTEXTO]
        except (ValueError, KeyError, TypeError):
            caso(rotulo + " — a saída não trouxe o contexto: %r" % saida,
                 False)
            continue
        ausentes = [f for f in FRASES_DAS_FORMAS if f not in esperadas]
        caso(rotulo, codigo == SILENCIO and not erro
             and bloco.get(CHAVE_DO_EVENTO) == EVENTO_DEPOIS_DA_FALHA
             and all(f in texto for f in esperadas)
             and not any(f in texto for f in ausentes))

    for rotulo, entrada in BANCADA_DO_SILENCIO:
        codigo, saida, erro = orientar_na_bancada(json.dumps(entrada))
        caso(rotulo, codigo == SILENCIO and saida == "" and erro == "")

    for rotulo, corpo in ENTRADAS_ILEGIVEIS:
        codigo, saida, erro = orientar_na_bancada(corpo)
        caso("entrada ilegível (%s): sai 0, sem JSON, uma linha de NÃO MEDIU "
             "no erro" % rotulo,
             codigo == SILENCIO and saida == ""
             and erro.count("\n") == 1 and "NÃO MEDIU" in erro)

    cp1252 = porta_da_frente_com_cp1252()
    caso("porta da frente com cp1252: JSON em UTF-8 estrito, evento %s e "
         "texto intacto%s" % (EVENTO_DEPOIS_DA_FALHA,
                              " — " + "; ".join(cp1252) if cp1252 else ""),
         not cp1252)
    ligacao = linha_da_orientacao_no_settings()
    caso("a linha chega: o settings.json chama este gancho no evento certo"
         + (" — " + "; ".join(ligacao) if ligacao else ""), not ligacao)

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: a orientação da recusa do isolamento — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
