import json
import os
import subprocess
import sys
from pathlib import Path

ONDE_AS_CERCAS_SAO_DECLARADAS = ".claude/settings.json"
CHAVE_DOS_GANCHOS = "hooks"
CHAVE_DO_COMANDO = "command"
CHAVE_DO_CASADOR = "matcher"
CASADOR_DE_TUDO = "*"
TEMPO_DE_UMA_CERCA_S = 30

COMO_A_OUTRA_FERRAMENTA_CHAMA_A_MESMA_COISA = {"write": "Write",
                                               "edit": "Edit",
                                               "notebook_edit": "NotebookEdit",
                                               "exec": "Bash",
                                               "shell_command": "Bash",
                                               "read": "Read",
                                               "ask_user_question": "AskUserQuestion"}

CHAVE_DA_RESPOSTA_LONGA = "hookSpecificOutput"
CHAVE_DA_DECISAO_LONGA = "permissionDecision"
CHAVE_DO_MOTIVO_LONGO = "permissionDecisionReason"
CHAVE_DA_DECISAO_CURTA = "decision"
CHAVE_DO_MOTIVO_CURTO = "reason"
CHAVE_DO_ENSINO = "additionalContext"
PALAVRA_QUE_BARRA_ONDE_NINGUEM_RESPONDE = ("deny", "block", "ask")
PALAVRA_QUE_RECUSA_NA_OUTRA = "block"
SAIDA_QUE_BARRA = 2
RECUSADO_SEM_MOTIVO_DITO = "recusado sem motivo dito"

COMO_O_ASSISTENTE_DO_EDITOR_CHAMA_A_MESMA_COISA = {
    "bash": "Bash", "powershell": "PowerShell", "edit": "Edit",
    "create": "Write", "write": "Write", "view": "Read", "read": "Read"}
CHAVE_DA_FERRAMENTA_NO_EDITOR = "toolName"
CHAVE_DOS_ARGUMENTOS_NO_EDITOR = "toolArgs"
CHAVE_DO_CWD_NO_EDITOR = "cwd"
RAIZ_QUE_A_OUTRA_FERRAMENTA_DA = "DEVIN_PROJECT_DIR"
RAIZ_QUE_AS_CERCAS_LEEM = "CLAUDE_PROJECT_DIR"
EVENTO_PADRAO = "PreToolUse"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_SEM_QUEM_RESPONDA = "bypassPermissions"


def raiz_do_repositorio(pedido=None):
    dito = (pedido or {}).get(CHAVE_DO_CWD_NO_EDITOR)
    return Path(os.environ.get(RAIZ_QUE_A_OUTRA_FERRAMENTA_DA) or dito
                or Path.cwd())


def veio_do_assistente_do_editor(pedido) -> bool:
    return CHAVE_DA_FERRAMENTA_NO_EDITOR in pedido


def no_dialeto_das_cercas(pedido):
    if not veio_do_assistente_do_editor(pedido):
        return pedido
    chegou = str(pedido.get(CHAVE_DA_FERRAMENTA_NO_EDITOR, ""))
    argumentos = pedido.get(CHAVE_DOS_ARGUMENTOS_NO_EDITOR) or {}
    return {"hook_event_name": EVENTO_PADRAO,
            "tool_name": COMO_O_ASSISTENTE_DO_EDITOR_CHAMA_A_MESMA_COISA.get(
                chegou.lower(), chegou),
            "tool_input": argumentos if isinstance(argumentos, dict) else {},
            CHAVE_DO_CWD_NO_EDITOR: pedido.get(CHAVE_DO_CWD_NO_EDITOR, "")}


def cercas_que_a_ferramenta_de_origem_rodaria(raiz, evento, ferramenta):
    arquivo = raiz / ONDE_AS_CERCAS_SAO_DECLARADAS
    if not arquivo.exists():
        return
    declarado = json.loads(arquivo.read_text(encoding="utf-8"))
    for grupo in declarado.get(CHAVE_DOS_GANCHOS, {}).get(evento, []):
        casador = grupo.get(CHAVE_DO_CASADOR, CASADOR_DE_TUDO)
        if casador != CASADOR_DE_TUDO and ferramenta not in casador.split("|"):
            continue
        for cerca in grupo.get(CHAVE_DOS_GANCHOS, []):
            if cerca.get(CHAVE_DO_COMANDO):
                yield cerca[CHAVE_DO_COMANDO]


def a_recusa_e_o_ensino_de_uma_cerca(saida, codigo):
    if codigo == SAIDA_QUE_BARRA:
        return saida.strip() or RECUSADO_SEM_MOTIVO_DITO, None
    ensino = None
    for linha in saida.splitlines():
        linha = linha.strip()
        if not linha.startswith("{"):
            continue
        try:
            dito = json.loads(linha)
        except json.JSONDecodeError:
            continue
        longa = dito.get(CHAVE_DA_RESPOSTA_LONGA, {})
        if longa.get(CHAVE_DA_DECISAO_LONGA) in PALAVRA_QUE_BARRA_ONDE_NINGUEM_RESPONDE:
            return longa.get(CHAVE_DO_MOTIVO_LONGO, ""), None
        if dito.get(CHAVE_DA_DECISAO_CURTA) in PALAVRA_QUE_BARRA_ONDE_NINGUEM_RESPONDE:
            return dito.get(CHAVE_DO_MOTIVO_CURTO, ""), None
        ensino = ensino or longa.get(CHAVE_DO_ENSINO)
    return None, ensino


def pergunta_para_as_cercas(pedido_da_outra_ferramenta, ferramenta):
    pergunta = dict(pedido_da_outra_ferramenta, tool_name=ferramenta)
    pergunta.setdefault(CAMPO_DO_MODO_DE_PERMISSAO, MODO_SEM_QUEM_RESPONDA)
    return pergunta


def a_recusa_e_o_ensino_da_camada(pedido_da_outra_ferramenta):
    raiz = raiz_do_repositorio(pedido_da_outra_ferramenta)
    pedido_da_outra_ferramenta = no_dialeto_das_cercas(pedido_da_outra_ferramenta)
    chegou = pedido_da_outra_ferramenta.get("tool_name", "")
    evento = pedido_da_outra_ferramenta.get("hook_event_name", EVENTO_PADRAO)
    ferramenta = COMO_A_OUTRA_FERRAMENTA_CHAMA_A_MESMA_COISA.get(chegou, chegou)

    pergunta = pergunta_para_as_cercas(pedido_da_outra_ferramenta, ferramenta)
    ambiente = dict(os.environ, **{RAIZ_QUE_AS_CERCAS_LEEM: str(raiz)})

    ensinos = []
    for comando in cercas_que_a_ferramenta_de_origem_rodaria(raiz, evento,
                                                             ferramenta):
        try:
            corrida = subprocess.run(comando, shell=True, cwd=raiz, env=ambiente,
                                     input=json.dumps(pergunta),
                                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                                     timeout=TEMPO_DE_UMA_CERCA_S)
        except (subprocess.SubprocessError, OSError):
            continue
        recusa, ensino = a_recusa_e_o_ensino_de_uma_cerca(
            corrida.stdout + corrida.stderr, corrida.returncode)
        if recusa is not None:
            return recusa, None
        if ensino:
            ensinos.append(ensino)
    return None, "\n".join(ensinos) or None


BANDEIRA_DE_TESTE = "--testar"
RECUSA_LONGA = ('{"hookSpecificOutput": {"permissionDecision": "deny", '
                '"permissionDecisionReason": "porque sim"}}')
RECUSA_CURTA = '{"decision": "block", "reason": "porque nao"}'
ENSINO = ('{"hookSpecificOutput": {"additionalContext": "cuidado com isso"}}')
LIBERADO = '{"hookSpecificOutput": {"permissionDecision": "allow"}}'
PERGUNTA = ('{"hookSpecificOutput": {"permissionDecision": "ask", '
            '"permissionDecisionReason": "quem decide e o dono"}}')
SETTINGS_DE_TESTE = {
    "hooks": {"PreToolUse": [
        {"matcher": "Write|Edit", "hooks": [{"command": "cerca-da-escrita"}]},
        {"matcher": "Bash", "hooks": [{"command": "cerca-do-shell"}]},
        {"hooks": [{"command": "cerca-de-tudo"}]}]}}

CASOS_DA_RESPOSTA = (
    ("recusa no dialeto longo", RECUSA_LONGA, 0, "porque sim", None),
    ("recusa no dialeto curto", RECUSA_CURTA, 0, "porque nao", None),
    ("recusa so pelo codigo de saida", "", SAIDA_QUE_BARRA,
     RECUSADO_SEM_MOTIVO_DITO, None),
    ("ensino nao e recusa", ENSINO, 0, None, "cuidado com isso"),
    ("liberado nao inventa recusa", LIBERADO, 0, None, None),
    ("silencio deixa passar", "", 0, None, None),
    ("lixo antes do json nao atrapalha", "ruido\n" + RECUSA_CURTA, 0,
     "porque nao", None),
    ("json quebrado nao derruba", "{nao e json}", 0, None, None),
    ("pergunta barra onde ninguem responde", PERGUNTA, 0,
     "quem decide e o dono", None))

CASOS_DO_NOME = (("write", "Write"), ("edit", "Edit"), ("exec", "Bash"),
                 ("shell_command", "Bash"), ("read", "Read"),
                 ("notebook_edit", "NotebookEdit"),
                 ("ask_user_question", "AskUserQuestion"),
                 ("glob", "glob"))

CASOS_DO_EDITOR = (
    ({"toolName": "bash", "toolArgs": {"command": "rm x"}, "cwd": "/r"},
     {"hook_event_name": "PreToolUse", "tool_name": "Bash",
      "tool_input": {"command": "rm x"}, "cwd": "/r"}),
    ({"toolName": "create", "toolArgs": {"file_path": "a.py"}},
     {"hook_event_name": "PreToolUse", "tool_name": "Write",
      "tool_input": {"file_path": "a.py"}, "cwd": ""}),
    ({"tool_name": "exec", "tool_input": {"command": "ls"}},
     {"tool_name": "exec", "tool_input": {"command": "ls"}}),
)

CASOS_DO_CASADOR = (("Write", ["cerca-da-escrita", "cerca-de-tudo"]),
                    ("Bash", ["cerca-do-shell", "cerca-de-tudo"]),
                    ("Read", ["cerca-de-tudo"]))

FALHA = "  FALHA {}: esperado {!r}, veio {!r}"
PLACAR = "ponte: {} de {} casos"


def testar():
    import tempfile
    quebrou = 0
    for nome, saida, codigo, recusa, ensino in CASOS_DA_RESPOSTA:
        veio = a_recusa_e_o_ensino_de_uma_cerca(saida, codigo)
        if veio != (recusa, ensino):
            quebrou += 1
            print(FALHA.format(nome, (recusa, ensino), veio))
    for chegou, esperado in CASOS_DO_NOME:
        veio = COMO_A_OUTRA_FERRAMENTA_CHAMA_A_MESMA_COISA.get(chegou, chegou)
        if veio != esperado:
            quebrou += 1
            print(FALHA.format(f"nome {chegou}", esperado, veio))
    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / ONDE_AS_CERCAS_SAO_DECLARADAS
        alvo.parent.mkdir(parents=True)
        alvo.write_text(json.dumps(SETTINGS_DE_TESTE), encoding="utf-8")
        for ferramenta, esperado in CASOS_DO_CASADOR:
            veio = list(cercas_que_a_ferramenta_de_origem_rodaria(
                Path(tmp), EVENTO_PADRAO, ferramenta))
            if veio != esperado:
                quebrou += 1
                print(FALHA.format(f"casador {ferramenta}", esperado, veio))
        vazio = list(cercas_que_a_ferramenta_de_origem_rodaria(
            Path(tmp) / "nao-existe", EVENTO_PADRAO, "Write"))
        if vazio != []:
            quebrou += 1
            print(FALHA.format("sem settings", [], vazio))
    for pedido, esperado in CASOS_DO_EDITOR:
        veio = no_dialeto_das_cercas(pedido)
        if veio != esperado:
            quebrou += 1
            print(FALHA.format("dialeto do editor", esperado, veio))
    saida_do_editor = resposta_para_quem_perguntou(
        {"toolName": "bash"}, "porque sim")
    if saida_do_editor != {"permissionDecision": "deny",
                           "permissionDecisionReason": "porque sim"}:
        quebrou += 1
        print(FALHA.format("resposta ao editor", "deny", saida_do_editor))
    sem_modo = pergunta_para_as_cercas({"tool_name": "exec"}, "Bash")
    if sem_modo.get(CAMPO_DO_MODO_DE_PERMISSAO) != MODO_SEM_QUEM_RESPONDA:
        quebrou += 1
        print(FALHA.format("pedido sem modo declara que ninguem responde",
                           MODO_SEM_QUEM_RESPONDA, sem_modo))
    com_modo = pergunta_para_as_cercas(
        {"tool_name": "exec", CAMPO_DO_MODO_DE_PERMISSAO: "default"}, "Bash")
    if com_modo.get(CAMPO_DO_MODO_DE_PERMISSAO) != "default":
        quebrou += 1
        print(FALHA.format("modo que a outra ferramenta declarou fica",
                           "default", com_modo))
    saida_da_outra = resposta_para_quem_perguntou({"tool_name": "exec"}, "x")
    if saida_da_outra != {"decision": "block", "reason": "x"}:
        quebrou += 1
        print(FALHA.format("resposta a outra ferramenta", "block", saida_da_outra))
    total = (len(CASOS_DA_RESPOSTA) + len(CASOS_DO_NOME)
             + len(CASOS_DO_CASADOR) + 1 + len(CASOS_DO_EDITOR) + 4)
    print(PLACAR.format(total - quebrou, total))
    return 1 if quebrou else 0



def resposta_para_quem_perguntou(pedido, recusa):
    if veio_do_assistente_do_editor(pedido):
        return {CHAVE_DA_DECISAO_LONGA: "deny", CHAVE_DO_MOTIVO_LONGO: recusa}
    return {CHAVE_DA_DECISAO_CURTA: PALAVRA_QUE_RECUSA_NA_OUTRA,
            CHAVE_DO_MOTIVO_CURTO: recusa}


def main():
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    try:
        pedido = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    recusa, ensino = a_recusa_e_o_ensino_da_camada(pedido)
    if recusa is None:
        if ensino and not veio_do_assistente_do_editor(pedido):
            print(json.dumps({CHAVE_DA_RESPOSTA_LONGA: {CHAVE_DO_ENSINO: ensino}},
                             ensure_ascii=False))
        return 0
    print(json.dumps(resposta_para_quem_perguntou(pedido, recusa),
                     ensure_ascii=False))
    return 0 if veio_do_assistente_do_editor(pedido) else SAIDA_QUE_BARRA


if __name__ == "__main__":
    sys.exit(main())
