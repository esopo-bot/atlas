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

CHAVE_DO_CWD = "cwd"
RAIZ_QUE_A_OUTRA_FERRAMENTA_DA = "DEVIN_PROJECT_DIR"
RAIZ_QUE_AS_CERCAS_LEEM = "CLAUDE_PROJECT_DIR"
EVENTO_PADRAO = "PreToolUse"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_SEM_QUEM_RESPONDA = "bypassPermissions"

BANDEIRA_DO_CODEX = "--codex"
FERRAMENTA_DE_PATCH_DO_CODEX = "apply_patch"
CAMPO_DO_COMANDO = "command"
MARCA_DE_ARQUIVO_NOVO = "*** Add File: "
MARCA_DE_ARQUIVO_MUDADO = "*** Update File: "
MARCA_DE_ARQUIVO_APAGADO = "*** Delete File: "
MARCA_DE_FIM_DO_PATCH = "*** End Patch"
MARCA_DE_TRECHO = "@@"
COMANDO_QUE_APAGA = "rm"
CHAVE_DO_NOME_DO_EVENTO = "hookEventName"
EVENTO_DE_PARADA = "Stop"


def escritas_de_um_patch(patch: str) -> list:
    escritas, atual = [], None

    def fechar():
        if not atual:
            return
        ferramenta, caminho, tiradas, postas = atual
        if ferramenta == "Write":
            escritas.append(("Write", {"file_path": caminho,
                                       "content": "\n".join(postas)}))
        else:
            escritas.append(("Edit", {"file_path": caminho,
                                      "old_string": "\n".join(tiradas),
                                      "new_string": "\n".join(postas)}))

    for linha in str(patch).splitlines():
        if linha.startswith(MARCA_DE_ARQUIVO_NOVO):
            fechar()
            atual = ("Write", linha[len(MARCA_DE_ARQUIVO_NOVO):].strip(),
                     [], [])
        elif linha.startswith(MARCA_DE_ARQUIVO_MUDADO):
            fechar()
            atual = ("Edit", linha[len(MARCA_DE_ARQUIVO_MUDADO):].strip(),
                     [], [])
        elif linha.startswith(MARCA_DE_ARQUIVO_APAGADO):
            fechar()
            atual = None
            caminho = linha[len(MARCA_DE_ARQUIVO_APAGADO):].strip()
            escritas.append(("Bash", {CAMPO_DO_COMANDO:
                                      f"{COMANDO_QUE_APAGA} {caminho}"}))
        elif linha.startswith(MARCA_DE_FIM_DO_PATCH):
            fechar()
            atual = None
        elif atual is None or linha.startswith(MARCA_DE_TRECHO):
            continue
        elif linha.startswith("+"):
            atual[3].append(linha[1:])
        elif linha.startswith("-"):
            atual[2].append(linha[1:])
        else:
            atual[2].append(linha[1:])
            atual[3].append(linha[1:])
    fechar()
    return escritas


def pedidos_no_dialeto_do_codex(pedido: dict) -> list:
    chegou = pedido.get("tool_name", "")
    entrada = pedido.get("tool_input") or {}
    if chegou == FERRAMENTA_DE_PATCH_DO_CODEX:
        return [dict(pedido, tool_name=ferramenta, tool_input=escrita)
                for ferramenta, escrita in escritas_de_um_patch(
                    entrada.get(CAMPO_DO_COMANDO, ""))]
    comando = entrada.get(CAMPO_DO_COMANDO)
    if isinstance(comando, list):
        entrada = dict(entrada, **{CAMPO_DO_COMANDO: " ".join(map(str, comando))})
        return [dict(pedido, tool_input=entrada)]
    return [pedido]


def raiz_do_repositorio(pedido=None):
    dito = (pedido or {}).get(CHAVE_DO_CWD)
    return Path(os.environ.get(RAIZ_QUE_A_OUTRA_FERRAMENTA_DA) or dito
                or Path.cwd())


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


def comando_com_a_raiz_expandida(comando: str, raiz) -> str:
    raiz_posix = str(raiz).replace("\\", "/")
    return (comando.replace("${" + RAIZ_QUE_AS_CERCAS_LEEM + "}", raiz_posix)
            .replace("$" + RAIZ_QUE_AS_CERCAS_LEEM, raiz_posix))


def pergunta_para_as_cercas(pedido_da_outra_ferramenta, ferramenta):
    pergunta = dict(pedido_da_outra_ferramenta, tool_name=ferramenta)
    pergunta.setdefault(CAMPO_DO_MODO_DE_PERMISSAO, MODO_SEM_QUEM_RESPONDA)
    return pergunta


def a_recusa_e_o_ensino_da_camada(pedido_da_outra_ferramenta, codex=False):
    pedidos = (pedidos_no_dialeto_do_codex(pedido_da_outra_ferramenta)
               if codex else [pedido_da_outra_ferramenta])
    ensinos = []
    for pedido in pedidos:
        recusa, ensino = a_recusa_e_o_ensino_de_um_pedido(pedido)
        if recusa is not None:
            return recusa, None
        if ensino:
            ensinos.append(ensino)
    return None, "\n".join(ensinos) or None


def a_recusa_e_o_ensino_de_um_pedido(pedido_da_outra_ferramenta):
    raiz = raiz_do_repositorio(pedido_da_outra_ferramenta)
    chegou =pedido_da_outra_ferramenta.get("tool_name", "")
    evento = pedido_da_outra_ferramenta.get("hook_event_name", EVENTO_PADRAO)
    ferramenta = COMO_A_OUTRA_FERRAMENTA_CHAMA_A_MESMA_COISA.get(chegou, chegou)

    pergunta = pergunta_para_as_cercas(pedido_da_outra_ferramenta, ferramenta)
    ambiente = dict(os.environ, **{RAIZ_QUE_AS_CERCAS_LEEM: str(raiz)})

    ensinos = []
    for comando in cercas_que_a_ferramenta_de_origem_rodaria(raiz, evento,
                                                             ferramenta):
        comando = comando_com_a_raiz_expandida(comando, raiz)
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


CASOS_DO_CASADOR = (("Write", ["cerca-da-escrita", "cerca-de-tudo"]),
                    ("Bash", ["cerca-do-shell", "cerca-de-tudo"]),
                    ("Read", ["cerca-de-tudo"]))

PATCH_DE_EXEMPLO = """*** Begin Patch
*** Add File: novo.py
+import os
+print(os.name)
*** Update File: velho.py
@@ def f():
 contexto
-antigo
+novo
*** Delete File: fora.py
*** End Patch"""
PEDIDO_DE_PATCH = {"hook_event_name": "PreToolUse",
                   "tool_name": "apply_patch",
                   "tool_input": {"command": PATCH_DE_EXEMPLO}}
CERCA_QUE_BARRA_A_PARADA = 'print(\'{"decision": "block", "reason": "falta x"}\')\n'
TEMPO_DA_PONTE_VISTA_DE_FORA_S = 60


def a_parada_do_codex_vista_de_fora():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cerca = Path(tmp) / "cerca.py"
        cerca.write_text(CERCA_QUE_BARRA_A_PARADA, encoding="utf-8")
        declarado = Path(tmp) / ONDE_AS_CERCAS_SAO_DECLARADAS
        declarado.parent.mkdir(parents=True)
        declarado.write_text(json.dumps({CHAVE_DOS_GANCHOS: {EVENTO_DE_PARADA: [
            {CHAVE_DOS_GANCHOS: [
                {CHAVE_DO_COMANDO: f'"{sys.executable}" "{cerca}"'}]}]}}),
            encoding="utf-8")
        corrida = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), BANDEIRA_DO_CODEX],
            input=json.dumps({"hook_event_name": EVENTO_DE_PARADA}),
            env=dict(os.environ, **{RAIZ_QUE_A_OUTRA_FERRAMENTA_DA: tmp}),
            capture_output=True, text=True, encoding="utf-8",
            timeout=TEMPO_DA_PONTE_VISTA_DE_FORA_S)
        return corrida.returncode, json.loads(corrida.stdout or "null")


CERCA_NOVA_QUE_BARRA = ('import json\nprint(json.dumps({"hookSpecificOutput": '
                        '{"permissionDecision": "deny", '
                        '"permissionDecisionReason": "falta y"}}))\n')
PROGRAMA_QUE_RODA_A_CERCA = (
    "import os,sys,runpy;"
    "r=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd();"
    "a=os.path.join(r,sys.argv[1]);"
    "sys.argv=[a];sys.path[0]=os.path.dirname(a);"
    "runpy.run_path(a,run_name='__main__')")


def a_cerca_sem_variavel_no_texto_vista_de_fora():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cerca = Path(tmp) / ".claude" / "hooks" / "cerca-nova.py"
        cerca.parent.mkdir(parents=True)
        cerca.write_text(CERCA_NOVA_QUE_BARRA, encoding="utf-8")
        (Path(tmp) / ONDE_AS_CERCAS_SAO_DECLARADAS).write_text(json.dumps(
            {CHAVE_DOS_GANCHOS: {EVENTO_PADRAO: [
                {CHAVE_DO_CASADOR: "Bash", CHAVE_DOS_GANCHOS: [
                    {CHAVE_DO_COMANDO: f'"{sys.executable}" -c '
                                       f'"{PROGRAMA_QUE_RODA_A_CERCA}" '
                                       '.claude/hooks/cerca-nova.py'}]}]}}),
            encoding="utf-8")
        ambiente = {k: v for k, v in os.environ.items()
                    if k != RAIZ_QUE_AS_CERCAS_LEEM}
        ambiente[RAIZ_QUE_A_OUTRA_FERRAMENTA_DA] = tmp
        corrida = subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=json.dumps({"tool_name": "exec",
                              "tool_input": {"command": "ls"}}),
            env=ambiente, capture_output=True, text=True, encoding="utf-8",
            timeout=TEMPO_DA_PONTE_VISTA_DE_FORA_S)
        return corrida.returncode, json.loads(corrida.stdout or "null")


def casos_do_codex():
    return (
        ("patch: arquivo novo vira Write com o conteúdo das linhas postas",
         escritas_de_um_patch(PATCH_DE_EXEMPLO)[0],
         ("Write", {"file_path": "novo.py",
                    "content": "import os\nprint(os.name)"})),
        ("patch: arquivo mudado vira Edit com o que saiu e o que entrou",
         escritas_de_um_patch(PATCH_DE_EXEMPLO)[1],
         ("Edit", {"file_path": "velho.py", "old_string": "contexto\nantigo",
                   "new_string": "contexto\nnovo"})),
        ("patch: arquivo apagado vira o comando que apaga",
         escritas_de_um_patch(PATCH_DE_EXEMPLO)[2],
         ("Bash", {"command": "rm fora.py"})),
        ("o pedido de patch vira um pedido por arquivo, no nome das cercas",
         [p["tool_name"] for p in pedidos_no_dialeto_do_codex(PEDIDO_DE_PATCH)],
         ["Write", "Edit", "Bash"]),
        ("comando de shell em lista vira uma linha só",
         pedidos_no_dialeto_do_codex(
             {"tool_name": "Bash",
              "tool_input": {"command": ["git", "push"]}})[0]["tool_input"],
         {"command": "git push"}),
        ("pedido comum passa inteiro e sozinho",
         pedidos_no_dialeto_do_codex({"tool_name": "Read", "tool_input": {}}),
         [{"tool_name": "Read", "tool_input": {}}]),
        ("recusa para o codex sai no dialeto longo com o nome do evento",
         resposta_para_quem_perguntou(PEDIDO_DE_PATCH, "porque sim", codex=True),
         {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": "porque sim"}}),
        ("na parada, a recusa para o codex sai no dialeto curto",
         resposta_para_quem_perguntou({"hook_event_name": "Stop"}, "falta x",
                                      codex=True),
         {"decision": "block", "reason": "falta x"}),
        ("a raiz entra no comando da cerca antes do shell, porque o cmd do "
         "Windows não expande ${VAR}",
         comando_com_a_raiz_expandida(
             'python "${CLAUDE_PROJECT_DIR}/x.py" $CLAUDE_PROJECT_DIR',
             Path("D:\\r")),
         'python "D:/r/x.py" D:/r'),
        ("ensino para o codex leva o nome do evento",
         ensino_para_quem_perguntou({"hook_event_name": "SessionStart"}, "oi",
                                    codex=True),
         {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                 "additionalContext": "oi"}}),
        ("na parada, o codex recebe o bloqueio no JSON e a ponte sai sem erro, "
         "porque o PowerShell que roda o gancho no Windows troca o 2 por 1",
         a_parada_do_codex_vista_de_fora(),
         (0, {"decision": "block", "reason": "falta x"})),
        ("cerca declarada sem variável no texto do comando, que acha a raiz "
         "pelo ambiente, barra o Devin pela ponte com a saída que barra",
         a_cerca_sem_variavel_no_texto_vista_de_fora(),
         (2, {"decision": "block", "reason": "falta y"})),
    )
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
    sem_modo =pergunta_para_as_cercas({"tool_name": "exec"}, "Bash")
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
    casos_do_codex_medidos = casos_do_codex()
    for nome, veio, esperado in casos_do_codex_medidos:
        if veio != esperado:
            quebrou += 1
            print(FALHA.format(nome, esperado, veio))
    total = (len(CASOS_DA_RESPOSTA) + len(CASOS_DO_NOME)
             + len(CASOS_DO_CASADOR) + 1 + 3
             + len(casos_do_codex_medidos))
    print(PLACAR.format(total - quebrou, total))
    return 1 if quebrou else 0



def resposta_para_quem_perguntou(pedido, recusa, codex=False):
    evento =pedido.get("hook_event_name", EVENTO_PADRAO)
    if codex and evento == EVENTO_PADRAO:
        return {CHAVE_DA_RESPOSTA_LONGA: {
            CHAVE_DO_NOME_DO_EVENTO: evento,
            CHAVE_DA_DECISAO_LONGA: "deny", CHAVE_DO_MOTIVO_LONGO: recusa}}
    return {CHAVE_DA_DECISAO_CURTA: PALAVRA_QUE_RECUSA_NA_OUTRA,
            CHAVE_DO_MOTIVO_CURTO: recusa}


def ensino_para_quem_perguntou(pedido, ensino, codex=False):
    resposta = {CHAVE_DO_ENSINO: ensino}
    if codex:
        resposta[CHAVE_DO_NOME_DO_EVENTO] = pedido.get("hook_event_name",
                                                       EVENTO_PADRAO)
    return {CHAVE_DA_RESPOSTA_LONGA: resposta}


def codigo_de_saida_da_recusa(pedido, codex=False):
    if codex:
        return 0
    return SAIDA_QUE_BARRA


def main():
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    codex = BANDEIRA_DO_CODEX in sys.argv[1:]
    try:
        pedido = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    recusa, ensino = a_recusa_e_o_ensino_da_camada(pedido, codex)
    if recusa is None:
        if ensino:
            print(json.dumps(ensino_para_quem_perguntou(pedido, ensino, codex),
                             ensure_ascii=False))
        return 0
    print(json.dumps(resposta_para_quem_perguntou(pedido, recusa, codex),
                     ensure_ascii=False))
    return codigo_de_saida_da_recusa(pedido, codex)


if __name__ == "__main__":
    sys.exit(main())
