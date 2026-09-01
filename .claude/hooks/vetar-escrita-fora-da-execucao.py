import json
import os
import re
import sys
import tempfile
from pathlib import Path

MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
EXPANSAO_QUE_ASPA_DUPLA_NAO_SEGURA = re.compile(r"\$\(|`|\)")
DOCUMENTO_LITERAL_QUE_NAO_EXPANDE = re.compile(
    r"<<-?\s*(['\"])(\w+)\1.*?(?:^\2\s*$|\Z)", re.S | re.M)
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&<>]+)")
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"

COMANDO_CD = "cd"
NOMES_DO_GIT = ("git", "git.exe")

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}
BANDEIRA_DO_DIRETORIO_DO_GIT = ("-C",)

VERBOS_DO_GIT_QUE_ESCREVEM = {
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "commit",
    "init", "merge", "mv", "push", "rebase", "reset", "restore", "revert",
    "rm", "stash", "switch"}
VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO = {
    "branch": {"--show-current", "--list", "-l", "-a", "--all", "-r",
               "--remotes", "-v", "-vv", "--verbose", "--contains",
               "--merged", "--no-merged", "--points-at"},
    "tag": {"--list", "-l", "-n", "--contains", "--points-at", "--merged"},
}

COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS = ("rm", "rmdir", "mv", "tee", "touch",
                                        "mkdir", "truncate", "chmod", "chown")
COMANDOS_QUE_ESCREVEM_NO_ULTIMO = ("cp", "ln", "install")
COMANDO_QUE_ESCREVE_NO_LUGAR = "sed"
PROGRAMAS_COM_REDIRECIONAMENTO_PROPRIO = ("awk", "gawk", "mawk", "nawk")
REDIRECIONAMENTO_DE_DENTRO = re.compile(
    r">>?\s*[\"']([^\"']+)[\"']")
BANDEIRA_DE_ESCRITA_NO_LUGAR = "-i"
BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO = "--in-place"

COMANDO_DD = "dd"
PREFIXO_DA_SAIDA_DO_DD = "of="

COMANDO_TAR = "tar"
BANDEIRAS_DE_EXTRACAO_DO_TAR = ("--extract", "--get")
BANDEIRAS_DE_CRIACAO_DO_TAR = ("--create",)
LETRA_DE_EXTRACAO_DO_TAR = "x"
LETRA_DE_CRIACAO_DO_TAR = "c"
LETRA_DO_ARQUIVO_DO_TAR = "f"
BANDEIRAS_DO_DIRETORIO_DO_TAR = ("-C", "--directory")
BANDEIRAS_DO_ARQUIVO_DO_TAR = ("-f", "--file")

COMANDOS_COM_DESTINO_POR_BANDEIRA = ("cp", "mv", "ln", "install")
BANDEIRAS_DO_DESTINO = ("-t", "--target-directory")

PREFIXO_DE_BANDEIRA = "-"
PREFIXO_DE_BANDEIRA_LONGA = "--"
DIRETORIO_CORRENTE = "."

PREFIXO_DOS_DISPOSITIVOS = "/dev/"

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_VERBO = -1
SEM_NOME = ""
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
LIMITE_CONFESSADO = (
    "O que esta cerca NÃO cobre, dito de frente para ninguém confiar "
    "demais nela: ela lê o COMANDO, não o que o programa faz por dentro. "
    "Escrita decidida dentro de um documento literal — `python3 - <<'PY' "
    "... PY`, e o mesmo com qualquer interpretador — atravessa sem ser "
    "vista. Isso não é permissão: é o limite do instrumento, e quem "
    "escreve fora da raiz por ali continua perdendo o trabalho na pasta "
    "temporária."
)

RECUSA = (
    "Regra 16 da camada: isto quer escrever em {!r}, que resolve para {} — "
    "fora da raiz desta execução, que é {}. Arquivo escrito fora da árvore "
    "não entra no commit desta branch de trabalho e some com a pasta que o "
    "guardou: a etapa seguinte encontra a árvore limpa e a execução termina "
    "sem entregar nada. Escreva DENTRO da raiz, de preferência por caminho "
    "relativo, e commite na branch de trabalho antes de fechar a sua "
    "evidência. Ler continua livre: `cat`, `grep`, `git log` e `sed -n` "
    "passam, aqui e lá fora. Esta cerca só existe enquanto uma etapa do "
    "executor de roteiros estiver rodando — é a marca {} no ambiente que a "
    "levanta; em sessão interativa do dono ela não morde.\n"
    + LIMITE_CONFESSADO
)
APRENDIZADO = (
    "durante etapa do executor de roteiros, escrever fora da raiz da "
    "execução é recusado: o caminho é relativo, dentro da árvore, e "
    "commitado na branch de trabalho."
)

PASTA_DO_RASCUNHO_DO_AGENTE = "claude-"
FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def a_cerca_esta_de_pe(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_DE_ETAPA_NO_AMBIENTE))


def raiz_da_execucao(entrada: dict, ambiente) -> Path:
    declarada = (ambiente or {}).get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    bruta = declarada or (entrada or {}).get("cwd") or os.getcwd()
    try:
        return Path(bruta).resolve(strict=False)
    except OSError:
        return Path(bruta)


def cortar_respeitando_aspas(comando: str):
    segmentos, atual, aspa_aberta = [], [], None
    i = 0
    while i < len(comando):
        c = comando[i]
        if aspa_aberta == ASPA_SIMPLES:
            atual.append(c)
            aspa_aberta = None if c == ASPA_SIMPLES else aspa_aberta
            i += 1
        elif aspa_aberta == ASPA_DUPLA and c == ASPA_DUPLA:
            atual.append(c)
            aspa_aberta = None
            i += 1
        elif aspa_aberta is None and c in ASPAS:
            atual.append(c)
            aspa_aberta = c
            i += 1
        elif corte := (EXPANSAO_QUE_ASPA_DUPLA_NAO_SEGURA if aspa_aberta
                       else SEPARADORES_DE_COMANDO).match(comando, i):
            segmentos.append("".join(atual))
            atual = []
            i = corte.end()
        else:
            atual.append(c)
            i += 1
    if aspa_aberta is not None:
        return None
    segmentos.append("".join(atual))
    return segmentos


def separar(comando: str) -> list:
    sem_documento = DOCUMENTO_LITERAL_QUE_NAO_EXPANDE.sub(" ", comando)
    segmentos = cortar_respeitando_aspas(sem_documento)
    aspas_nao_fecharam = segmentos is None
    if aspas_nao_fecharam:
        return SEPARADORES_DE_COMANDO.split(sem_documento)
    return segmentos


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def partir_em_tokens(segmento: str) -> list:
    try:
        import shlex
        tokens = shlex.split(segmento, posix=False)
    except ValueError:
        tokens = segmento.split()
    return [sem_o_par_de_aspas_que_envolve(t) for t in tokens]


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


def indice_do_verbo(tokens: list) -> int:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE:
            i += 2
            continue
        colada_por_igual = any(
            t.startswith(g + "=")
            for g in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE)
        if colada_por_igual or t in BANDEIRAS_GLOBAIS_SIMPLES:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        return i
    return SEM_VERBO


def valor_da_bandeira(tokens: list, bandeiras) -> str:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in bandeiras and i + 1 < len(tokens):
            return tokens[i + 1]
        for bandeira in bandeiras:
            if t.startswith(bandeira + "="):
                return t.split("=", 1)[1]
        i += 1
    return SEM_NOME


def argumento_faz_escrever(verbo: str, resto: list) -> bool:
    de_leitura = VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO[verbo]
    bandeiras = [t for t in resto if t.startswith("-")]
    posicionais = [t for t in resto if not t.startswith("-")]
    if any(b.split("=", 1)[0].lower() not in de_leitura for b in bandeiras):
        return True
    return bool(posicionais) and not bandeiras


def verbo_do_git_que_escreve(tokens: list) -> str:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_NOME
    verbo = tokens[i].lower()
    if verbo in VERBOS_DO_GIT_QUE_ESCREVEM:
        return verbo
    if verbo in VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO:
        return verbo if argumento_faz_escrever(verbo, tokens[i + 1:]) \
            else SEM_NOME
    return SEM_NOME


def letras_das_bandeiras_curtas(tokens: list) -> str:
    curtas = [t for t in tokens[1:]
              if t.startswith(PREFIXO_DE_BANDEIRA)
              and not t.startswith(PREFIXO_DE_BANDEIRA_LONGA)]
    return "".join(t[1:] for t in curtas)


def valor_depois_do_grupo_curto(tokens: list, letra: str) -> str:
    for i, token in enumerate(tokens):
        curta = token.startswith(PREFIXO_DE_BANDEIRA) \
            and not token.startswith(PREFIXO_DE_BANDEIRA_LONGA)
        if curta and token.endswith(letra) and i + 1 < len(tokens):
            return tokens[i + 1]
    return SEM_NOME


def caminho_escrito_pelo_git(tokens: list) -> str:
    if not verbo_do_git_que_escreve(tokens):
        return SEM_NOME
    return valor_da_bandeira(tokens, BANDEIRA_DO_DIRETORIO_DO_GIT) \
        or DIRETORIO_CORRENTE


def caminho_escrito_pelo_dd(tokens: list) -> str:
    for token in tokens[1:]:
        if token.startswith(PREFIXO_DA_SAIDA_DO_DD):
            return token[len(PREFIXO_DA_SAIDA_DO_DD):]
    return SEM_NOME


def caminho_escrito_pelo_tar(tokens: list) -> str:
    letras = letras_das_bandeiras_curtas(tokens)
    extrai = LETRA_DE_EXTRACAO_DO_TAR in letras \
        or any(b in tokens for b in BANDEIRAS_DE_EXTRACAO_DO_TAR)
    if extrai:
        return valor_da_bandeira(tokens, BANDEIRAS_DO_DIRETORIO_DO_TAR) \
            or DIRETORIO_CORRENTE
    cria = LETRA_DE_CRIACAO_DO_TAR in letras \
        or any(b in tokens for b in BANDEIRAS_DE_CRIACAO_DO_TAR)
    if cria:
        return valor_da_bandeira(tokens, BANDEIRAS_DO_ARQUIVO_DO_TAR) \
            or valor_depois_do_grupo_curto(tokens, LETRA_DO_ARQUIVO_DO_TAR)
    return SEM_NOME


def caminhos_escritos_por_bandeira(programa: str, tokens: list) -> list:
    if e_git(tokens[0]):
        return [caminho_escrito_pelo_git(tokens)]
    if programa == COMANDO_DD:
        return [caminho_escrito_pelo_dd(tokens)]
    if programa == COMANDO_TAR:
        return [caminho_escrito_pelo_tar(tokens)]
    if programa in COMANDOS_COM_DESTINO_POR_BANDEIRA:
        return [valor_da_bandeira(tokens, BANDEIRAS_DO_DESTINO)]
    return []


def caminhos_que_o_programa_redireciona(programa: str, tokens: list) -> list:
    if programa not in PROGRAMAS_COM_REDIRECIONAMENTO_PROPRIO:
        return []
    corpo = next((t for t in tokens[1:] if not t.startswith("-")), SEM_NOME)
    return [m.group(1)
            for m in REDIRECIONAMENTO_DE_DENTRO.finditer(corpo)]


def caminhos_escritos_pelo_segmento(segmento: str, tokens: list) -> list:
    escritos = [m.group(1)
                for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
    if tokens:
        programa = Path(tokens[0].replace("\\", "/")).name.lower()
        escritos += caminhos_que_o_programa_redireciona(programa, tokens)
        posicionais = [t for t in tokens[1:] if not t.startswith("-")]
        destino = valor_da_bandeira(tokens, BANDEIRAS_DO_DESTINO) \
            if programa in COMANDOS_COM_DESTINO_POR_BANDEIRA else SEM_NOME
        if programa in COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS:
            escritos += posicionais
        elif programa in COMANDOS_QUE_ESCREVEM_NO_ULTIMO and posicionais \
                and not destino:
            escritos.append(posicionais[-1])
        elif programa == COMANDO_QUE_ESCREVE_NO_LUGAR and any(
                t == BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO
                or t.startswith(BANDEIRA_DE_ESCRITA_NO_LUGAR)
                for t in tokens[1:] if t.startswith("-")):
            escritos += posicionais
        escritos += caminhos_escritos_por_bandeira(programa, tokens)
    return [sem_o_par_de_aspas_que_envolve(e) for e in escritos if e]


def resolver(caminho: str, onde: str):
    if not caminho:
        return None
    alvo = Path(os.path.expanduser(caminho))
    if not alvo.is_absolute():
        alvo = Path(onde or ".") / alvo
    try:
        return alvo.resolve(strict=False)
    except OSError:
        return None


def e_dispositivo(caminho: str) -> bool:
    return caminho.startswith(PREFIXO_DOS_DISPOSITIVOS)


def escritas_do_comando(comando: str, onde: str) -> list:
    escritas = []
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        for caminho in caminhos_escritos_pelo_segmento(segmento, tokens):
            escritas.append((caminho, resolver(caminho, onde)))
        if tokens and Path(tokens[0]).name == COMANDO_CD and len(tokens) > 1:
            destino = resolver(sem_o_par_de_aspas_que_envolve(tokens[1]), onde)
            onde = str(destino) if destino else onde
    return escritas


def escritas_do_pedido(entrada: dict, onde: str) -> list:
    dado = (entrada or {}).get("tool_input") or {}
    if (entrada or {}).get("tool_name") in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [(dado[campo], resolver(dado[campo], onde))]
        return []
    comando = dado.get("command", "")
    return escritas_do_comando(comando, onde) if comando else []


def e_rascunho_do_agente(alvo) -> bool:
    try:
        dentro = alvo.resolve().relative_to(
            Path(tempfile.gettempdir()).resolve())
    except (ValueError, OSError):
        return False
    return bool(dentro.parts) and dentro.parts[0].startswith(
        PASTA_DO_RASCUNHO_DO_AGENTE)


def fora_da_raiz(declarado: str, alvo, raiz: Path) -> bool:
    if alvo is None or e_dispositivo(declarado):
        return False
    if e_rascunho_do_agente(alvo):
        return False
    return alvo != raiz and raiz not in alvo.parents


def recusa_do_pedido(entrada: dict, raiz: Path, onde: str):
    for declarado, alvo in escritas_do_pedido(entrada, onde):
        if fora_da_raiz(declarado, alvo, raiz):
            return declarado, alvo
    return None


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    if not a_cerca_esta_de_pe(os.environ):
        return SILENCIO
    try:
        entrada = json.load(sys.stdin)
        onde = entrada.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_da_execucao(entrada, os.environ)
    recusa = recusa_do_pedido(entrada, raiz, onde)
    if not recusa:
        return SILENCIO

    declarado, alvo = recusa
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": (
            RECUSA.format(declarado, alvo, raiz,
                          MARCA_DE_ETAPA_NO_AMBIENTE)
            + MANDA_GRAVAR.format(APRENDIZADO)),
    }}, ensure_ascii=False))
    return SILENCIO


def pedido_de_shell(comando: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


def pedido_de_escrita(ferramenta: str, caminho: str) -> dict:
    campo = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"tool_name": ferramenta, "tool_input": {campo: caminho}}


def montar_arvores_de_mentira(pasta: Path) -> None:
    (pasta / "raiz" / "sub").mkdir(parents=True, exist_ok=True)
    (pasta / "raiz" / "tmp").mkdir(parents=True, exist_ok=True)
    (pasta / "raiz" / "x.py").write_text("velho", encoding="utf-8")
    (pasta / "raiz-vizinha" / "sub").mkdir(parents=True, exist_ok=True)
    (pasta / "fora").mkdir(parents=True, exist_ok=True)
    (pasta / "fora" / "x.py").write_text("velho", encoding="utf-8")


def casos_que_barram(fora: str, vizinha: str) -> list:
    return [
        ("Write por caminho absoluto fora da raiz",
         pedido_de_escrita("Write", f"{fora}/novo.py")),
        ("Edit de arquivo que já existe fora",
         pedido_de_escrita("Edit", f"{fora}/x.py")),
        ("NotebookEdit fora",
         pedido_de_escrita("NotebookEdit", f"{fora}/n.ipynb")),
        ("redirecionamento para fora",
         pedido_de_shell(f"echo oi > {fora}/anotacao.txt")),
        ("redirecionamento que acrescenta fora",
         pedido_de_shell(f"echo oi >> {fora}/anotacao.txt")),
        ("copiar PARA fora",
         pedido_de_shell(f"cp raiz/x.py {fora}/copia.py")),
        ("mover PARA fora",
         pedido_de_shell(f"mv raiz/x.py {fora}/x.py")),
        ("apagar fora", pedido_de_shell(f"rm -rf {fora}/x.py")),
        ("criar pasta fora", pedido_de_shell(f"mkdir -p {fora}/nova")),
        ("sed no lugar fora", pedido_de_shell(f"sed -i 's/a/b/' {fora}/x.py")),
        ("tee fora", pedido_de_shell(f"echo oi | tee {fora}/x.txt")),
        ("touch fora", pedido_de_shell(f"touch {fora}/x.txt")),
        ("cd para fora e depois escrever por caminho relativo",
         pedido_de_shell(f"cd {fora} && echo oi > anotacao.txt")),
        ("pasta vizinha de nome parecido é fora, não dentro",
         pedido_de_escrita("Write", f"{vizinha}/sub/novo.py")),
    ]


def casos_dos_escapes_mecanicos(fora: str) -> list:
    return [
        ("git: verbo que escreve com -C para fora",
         pedido_de_shell(f"git -C {fora} commit -m mudanca")),
        ("git: init fora por -C", pedido_de_shell(f"git -C {fora} init")),
        ("dd: o valor de of= é o que ele escreve",
         pedido_de_shell(f"dd if=/dev/zero of={fora}/x.img bs=1 count=1")),
        ("tar: extração com -C para fora",
         pedido_de_shell(f"tar -xzf pacote.tar.gz -C {fora}")),
        ("tar: criação com -f escrevendo o pacote fora",
         pedido_de_shell(f"tar -czf {fora}/pacote.tar.gz sub")),
        ("tar: criação por bandeira longa fora",
         pedido_de_shell(f"tar --create --file={fora}/p.tar sub")),
        ("cp: destino por -t fora",
         pedido_de_shell(f"cp -t {fora} raiz/x.py")),
        ("mv: destino por --target-directory fora",
         pedido_de_shell(f"mv --target-directory={fora} raiz/x.py")),
        ("install: destino por -t fora",
         pedido_de_shell(f"install -t {fora} raiz/x.py")),
    ]


def casos_que_passam(raiz: str, fora: str) -> list:
    return [
        ("Write por caminho relativo dentro",
         pedido_de_escrita("Write", "sub/novo.py")),
        ("Write por caminho absoluto dentro",
         pedido_de_escrita("Write", f"{raiz}/sub/novo.py")),
        ("Edit dentro", pedido_de_escrita("Edit", f"{raiz}/x.py")),
        ("NotebookEdit dentro",
         pedido_de_escrita("NotebookEdit", "sub/n.ipynb")),
        ("a própria raiz não é fora dela mesma",
         pedido_de_shell(f"touch {raiz}")),
        ("redirecionamento dentro", pedido_de_shell("echo oi > tmp/x.txt")),
        ("mkdir dentro", pedido_de_shell("mkdir -p sub/nova")),
        ("cd para uma pasta de dentro e escrever lá",
         pedido_de_shell("cd sub && echo oi > x.txt")),
        ("o rascunho que o próprio agente recebe não é escrita fora",
         pedido_de_escrita(
             "Write",
             f"{tempfile.gettempdir()}/claude-1000/projeto/sessao/"
             "scratchpad/nota.md")),
        ("e escrever nele por shell também passa",
         pedido_de_shell(
             f"echo oi > {tempfile.gettempdir()}/claude-7/x/y/"
             "scratchpad/n.txt")),
        ("ler fora é livre", pedido_de_shell(f"cat {fora}/x.py")),
        ("varrer fora é livre", pedido_de_shell(f"grep -rn assunto {fora}")),
        ("git log fora é livre", pedido_de_shell(f"git -C {fora} log")),
        ("sed que só lê fora", pedido_de_shell(f"sed -n '1,5p' {fora}/x.py")),
        ("copiar DE fora para dentro",
         pedido_de_shell(f"cp {fora}/x.py sub/copia.py")),
        ("escrever em /dev/null não é escrever em arquivo",
         pedido_de_shell("python3 -m json.tool > /dev/null")),
        ("2>&1 não vira arquivo escrito",
         pedido_de_shell(f"git -C {fora} log 2>&1")),
        ("git que só lê continua livre com -C fora",
         pedido_de_shell(f"git -C {fora} status --porcelain")),
        ("tar que só lista o pacote lá fora",
         pedido_de_shell(f"tar -tzf {fora}/pacote.tar.gz")),
        ("tar que extrai aqui dentro",
         pedido_de_shell("tar -xzf pacote.tar.gz")),
        ("dd que lê de fora e escreve dentro",
         pedido_de_shell(f"dd if={fora}/x.py of=sub/copia.py")),
        ("cp DE fora para dentro com destino por -t",
         pedido_de_shell(f"cp -t sub {fora}/x.py")),
    ]


def testar() -> int:
    falhas, comportamento = [], []
    with tempfile.TemporaryDirectory(prefix="veto-fora-da-execucao-") as tmp:
        base = Path(tmp).resolve()
        montar_arvores_de_mentira(base)
        raiz = base / "raiz"
        fora = str(base / "fora")
        vizinha = str(base / "raiz-vizinha")
        onde = str(raiz)

        barra = casos_que_barram(fora, vizinha) \
            + casos_dos_escapes_mecanicos(fora)
        passa = casos_que_passam(str(raiz), fora)
        for rotulo, pedido in barra:
            if not recusa_do_pedido(pedido, raiz, onde):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, pedido in passa:
            recusa = recusa_do_pedido(pedido, raiz, onde)
            if recusa:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, recusa[0]))

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        caso("gancho que veta e não entende o pedido RECUSA, e nomeia a "
             "falha — quem não consegue julgar não pode dizer sim",
             recusou_sem_entender(TypeError("forma que o gancho não conhece")))
        caso("sem a marca da etapa no ambiente a cerca nem se levanta",
             not a_cerca_esta_de_pe({})
             and not a_cerca_esta_de_pe({"OUTRA": "1"}))
        caso("com a marca da etapa no ambiente a cerca se levanta",
             a_cerca_esta_de_pe({MARCA_DE_ETAPA_NO_AMBIENTE: "1"}))
        caso("a raiz declarada no ambiente manda",
             raiz_da_execucao({"cwd": fora},
                              {VARIAVEL_DA_RAIZ_DO_PROJETO: str(raiz)})
             == raiz)
        caso("sem raiz declarada, ela sai do cwd do pedido",
             raiz_da_execucao({"cwd": str(raiz)}, {}) == raiz)

        recusa = recusa_do_pedido(barra[0][1], raiz, onde) or ("", "")
        mensagem = (RECUSA.format(recusa[0], recusa[1], raiz,
                                  MARCA_DE_ETAPA_NO_AMBIENTE)
                    + MANDA_GRAVAR.format(APRENDIZADO))
        caso("a mensagem nomeia o caminho pedido", fora in mensagem)
        caso("a mensagem nomeia a raiz da execução", str(raiz) in mensagem)
        caso("a mensagem ensina o caminho que existe: escrever dentro e "
             "commitar", "commite" in mensagem and "DENTRO" in mensagem)
        caso("a mensagem diz que ler continua livre", "Ler continua livre"
             in mensagem)
        caso("a mensagem diz quem levanta a cerca",
             MARCA_DE_ETAPA_NO_AMBIENTE in mensagem)
        caso("a mensagem nomeia a regra 16, que é o que a motivou",
             "Regra 16" in mensagem)
        caso("a mensagem confessa o limite que o caso acima registra: "
             "escrita dentro de documento literal atravessa",
             "documento literal" in mensagem
             and "atravessa" in mensagem)
        caso("a mensagem manda gravar o aprendizado em conhecimento/, "
             "com a linha concreta",
             "regra 4" in mensagem and "`conhecimento/`" in mensagem
             and APRENDIZADO in mensagem)

        caso("entrada sem ferramenta nem comando não devolve escrita",
             escritas_do_pedido({}, onde) == [])
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(escritas_do_comando(
                 f"echo 'sem fechar > {fora}/x.txt", onde), list))
        caso("Write sem caminho não devolve escrita",
             escritas_do_pedido({"tool_name": "Write", "tool_input": {}},
                                onde) == [])
        caso("o gancho lê o comando, não o que o programa faz por dentro — "
             "limite confessado: escrita dentro de documento literal passa",
             not recusa_do_pedido(pedido_de_shell(
                 f"python3 - <<'PY'\nopen('{fora}/x','w')\nPY"), raiz, onde))
        caso("awk que redireciona por dentro do próprio programa é escrita, "
             "e a cerca passou a lê-lo",
             bool(recusa_do_pedido(pedido_de_shell(
                 "awk '{print > \"%s/x.txt\"}' raiz/x.py" % fora),
                 raiz, onde)))
        caso("awk que redireciona para DENTRO da raiz segue livre",
             not recusa_do_pedido(pedido_de_shell(
                 "awk '{print > \"sub/x.txt\"}' raiz/x.py"), raiz, onde))
        caso("awk que só lê não vira escrita",
             not recusa_do_pedido(pedido_de_shell(
                 "awk '{print $1}' %s/x.py" % fora), raiz, onde))

        falhas += [FALHA_COMPORTAMENTO.format(rotulo)
                   for rotulo, passou in comportamento if not passou]

    total = len(barra) + len(passa) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(barra), len(passa), len(comportamento)))
    return 0



def recusou_sem_entender(falha) -> bool:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        recusa_por_nao_entender(falha)
    try:
        dado = json.loads(saida.getvalue())["hookSpecificOutput"]
    except (ValueError, KeyError):
        return False
    return (dado.get("permissionDecision") == DECISAO_DE_NEGAR
            and type(falha).__name__
            in dado.get("permissionDecisionReason", ""))


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
