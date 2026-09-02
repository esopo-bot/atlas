import json
import os
import re
import sys
from pathlib import Path

PASTA_MODULOS = "modulos"
ORIGEM_SKILLS = ".agents/skills"
COPIA_SKILLS = ".claude/skills"
PASTA_DO_CONHECIMENTO = "conhecimento"
CARTAO_DO_MODULO = "LEIAME.md"
ARQUIVO_DE_PASTA_VAZIA = ".gitkeep"
CACHE_DE_EXECUCAO = "__pycache__"
SUFIXOS_COMPILADOS = (".pyc", ".pyo")

ABERTURA_DA_MARCA_DE_GERADO = "<!-- GERAD"
FONTE_NOMEADA_NA_MARCA = re.compile(r"[\w./-]+\.json")
JUNCAO_DE_FONTES = " e "

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
COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS = ("rm", "rmdir", "mv", "tee", "touch",
                                        "mkdir", "truncate", "chmod", "chown")
COMANDOS_QUE_ESCREVEM_NO_ULTIMO = ("cp", "ln", "install")
SUFIXOS_DE_ARQUIVO = (".py", ".md", ".json", ".yml", ".yaml", ".ts",
                      ".js", ".txt", ".jsonc")
INTERPRETADORES = ("python", "python3", "node", "nodejs", "ruby",
                   "perl", "php")
MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT = re.compile(
    r"""write|truncate|unlink|remove|rename|\bmkdir\b|['"]w[+bt]*['"]""")
ENTRE_ASPAS_SIMPLES = re.compile(r"'([^'\n]{3,300})'")
ENTRE_ASPAS_DUPLAS = re.compile(r'"([^"\n]{3,300})"')
COMANDO_QUE_ESCREVE_NO_LUGAR = "sed"
BANDEIRA_DE_ESCRITA_NO_LUGAR = "-i"
BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO = "--in-place"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
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
APRENDIZADO = (
    "cópia gerada não se edita à mão: edite a fonte, rode `python "
    "montar.py --sincronizar` e prove com `--verificar`."
)

RECUSA = (
    "Regra 15 da camada: isto quer escrever em {!r}, que é CÓPIA GERADA de "
    "{}. O que for escrito "
    "na cópia se perde na próxima sincronização, sem aviso nenhum: o "
    "instalador reescreve a cópia a partir da fonte, e a edição some junto "
    "com o motivo dela. O caminho é editar {} e rodar "
    "`python montar.py --sincronizar`; depois `python montar.py --verificar` "
    "para provar que ficou em dia — o --sincronizar escreve e não acusa, "
    "então rodar só ele deixa a divergência invisível. Ler a cópia continua "
    "livre."
)

MARCA_DE_MODULO_INSTALADO = "instalado:"
APRENDIZADO_MODULO_INSTALADO = (
    "cópia de módulo instalado também não se edita à mão: a fonte mora no "
    "repositório atlas, não aqui — edite lá e rode `python montar.py "
    "--atualizar` neste repositório."
)
RECUSA_MODULO_INSTALADO = (
    "Regra 15 da camada: isto quer escrever em {!r}, que é CÓPIA GERADA "
    "pelo módulo {} do atlas. Esta é uma instalação, não o repositório de "
    "desenvolvimento — não existe fonte local para editar aqui. O caminho "
    "é editar a fonte no repositório atlas (`modulos/{}/...`) e trazer a "
    "atualização com `python montar.py --atualizar`. Ler a cópia continua "
    "livre."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"

INSTALADOR = "montar.py"
SEM_INSTALADOR = (
    "COMPORTAMENTO [concordância com o {}]: não medido — {!r} não existe "
    "nesta árvore, e a concordância não se afirma sem os dois lados"
)
DIVERGENCIA_COM_O_INSTALADOR = (
    "só o gancho vê: {}; só o {} regenera: {}"
)


def e_territorio_do_repositorio(caminho: str) -> bool:
    partes = caminho.split("/")
    return len(partes) > 2 and partes[0] == PASTA_DO_CONHECIMENTO


def copias_de_espelho(raiz: Path) -> dict:
    origem, copia = raiz / ORIGEM_SKILLS, raiz / COPIA_SKILLS
    if not copia.is_dir():
        return {}
    achadas = {}
    for caminho in sorted(copia.rglob("*")):
        if not caminho.is_file():
            continue
        fonte = origem / caminho.relative_to(copia)
        achadas[caminho.relative_to(raiz).as_posix()] = \
            fonte.relative_to(raiz).as_posix()
    return achadas


def modulo_embutido_no_instalador(raiz: Path):
    import importlib.util
    alvo = raiz / INSTALADOR
    origem = importlib.util.spec_from_file_location("instalador", alvo)
    if origem is None or not alvo.is_file():
        return None
    instalador = importlib.util.module_from_spec(origem)
    try:
        origem.loader.exec_module(instalador)
    except Exception:
        return None
    return instalador


def copias_de_modulo_instalado(raiz: Path) -> dict:
    instalador = modulo_embutido_no_instalador(raiz)
    if instalador is None:
        return {}
    achadas = {}
    for nome, arquivos in instalador.MODULOS.items():
        for rotulo in arquivos:
            if instalador.e_territorio_do_repositorio(rotulo):
                continue
            if (raiz / rotulo).is_file():
                achadas[rotulo] = f"{MARCA_DE_MODULO_INSTALADO}{nome}"
    return achadas


def copias_de_modulo(raiz: Path) -> dict:
    origem = raiz / PASTA_MODULOS
    if not origem.is_dir():
        return copias_de_modulo_instalado(raiz)
    achadas = {}
    for pasta in sorted(p for p in origem.iterdir() if p.is_dir()):
        for caminho in sorted(pasta.rglob("*")):
            if not caminho.is_file() \
                    or caminho.name == ARQUIVO_DE_PASTA_VAZIA \
                    or CACHE_DE_EXECUCAO in caminho.parts \
                    or caminho.suffix in SUFIXOS_COMPILADOS:
                continue
            rotulo = caminho.relative_to(pasta).as_posix()
            if rotulo == CARTAO_DO_MODULO \
                    or e_territorio_do_repositorio(rotulo) \
                    or not (raiz / rotulo).is_file():
                continue
            achadas[rotulo] = caminho.relative_to(raiz).as_posix()
    return achadas


def copias_geradas(raiz: Path) -> dict:
    return {**copias_de_modulo(raiz), **copias_de_espelho(raiz)}


def fonte_nomeada_na_marca(alvo: Path) -> str:
    try:
        with alvo.open(encoding="utf-8", errors="replace") as arquivo:
            primeira = arquivo.readline()
    except OSError:
        return SEM_NOME
    if not primeira.startswith(ABERTURA_DA_MARCA_DE_GERADO):
        return SEM_NOME
    return JUNCAO_DE_FONTES.join(FONTE_NOMEADA_NA_MARCA.findall(primeira))


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


def caminhos_escritos_pelo_segmento(segmento: str, tokens: list) -> list:
    escritos = [m.group(1)
                for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
    if tokens:
        programa = Path(tokens[0].replace("\\", "/")).name.lower()
        posicionais = [t for t in tokens[1:] if not t.startswith("-")]
        if programa in COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS:
            escritos += posicionais
        elif programa in COMANDOS_QUE_ESCREVEM_NO_ULTIMO and posicionais:
            escritos.append(posicionais[-1])
        elif programa == COMANDO_QUE_ESCREVE_NO_LUGAR and any(
                t == BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO
                or t.startswith(BANDEIRA_DE_ESCRITA_NO_LUGAR)
                for t in tokens[1:] if t.startswith("-")):
            escritos += posicionais
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


def relativo_a_raiz(caminho: str, raiz: Path, onde: str) -> str:
    alvo = resolver(caminho, onde)
    if alvo is None:
        return SEM_NOME
    try:
        return alvo.relative_to(raiz.resolve(strict=False)).as_posix()
    except (OSError, ValueError):
        return SEM_NOME


def o_comando_chama_interpretador(comando: str) -> bool:
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        if not tokens:
            continue
        programa = Path(tokens[0].replace("\\", "/")).name.lower()
        if programa in INTERPRETADORES:
            return True
    return False


def caminhos_escritos_dentro_do_script(comando: str) -> list:
    if not o_comando_chama_interpretador(comando):
        return []
    if not MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(comando):
        return []
    achados = [m.group(1) for m in ENTRE_ASPAS_SIMPLES.finditer(comando)]
    achados += [m.group(1) for m in ENTRE_ASPAS_DUPLAS.finditer(comando)]
    return [a for a in achados
            if "'" not in a and '"' not in a
            and ("/" in a or a.endswith(SUFIXOS_DE_ARQUIVO))]


def caminhos_escritos_pelo_comando(comando: str, onde: str) -> list:
    escritos = [(c, onde) for c in caminhos_escritos_dentro_do_script(comando)]
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        for caminho in caminhos_escritos_pelo_segmento(segmento, tokens):
            escritos.append((caminho, onde))
        if tokens and Path(tokens[0]).name == COMANDO_CD and len(tokens) > 1:
            destino = resolver(sem_o_par_de_aspas_que_envolve(tokens[1]), onde)
            onde = str(destino) if destino else onde
    return escritos


def caminhos_escritos_pelo_pedido(entrada: dict, onde: str) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        return [(dado[campo], onde)
                for campo in CAMPOS_DE_CAMINHO if dado.get(campo)]
    if ferramenta not in ("Bash", "PowerShell"):
        return []
    comando = dado.get("command", "")
    return caminhos_escritos_pelo_comando(comando, onde) if comando else []


def recusa_do_pedido(entrada: dict, raiz: Path, onde: str):
    escritos = caminhos_escritos_pelo_pedido(entrada, onde)
    if not escritos:
        return None
    geradas = copias_geradas(raiz)
    for caminho, daqui in escritos:
        rel = relativo_a_raiz(caminho, raiz, daqui)
        if not rel:
            continue
        fonte = geradas.get(rel) or fonte_nomeada_na_marca(raiz / rel)
        if fonte:
            return rel, fonte
    return None


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
        onde = entrada.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    recusa = recusa_do_pedido(entrada, raiz, onde)
    if not recusa:
        return SILENCIO

    copia, fonte = recusa
    if fonte.startswith(MARCA_DE_MODULO_INSTALADO):
        nome = fonte[len(MARCA_DE_MODULO_INSTALADO):]
        motivo = (RECUSA_MODULO_INSTALADO.format(copia, nome, nome)
                  + MANDA_GRAVAR.format(APRENDIZADO_MODULO_INSTALADO))
    else:
        motivo = (RECUSA.format(copia, fonte, fonte)
                  + MANDA_GRAVAR.format(APRENDIZADO))
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": motivo,
    }}, ensure_ascii=False))
    return SILENCIO


SKILL_ESPELHADA = "verificacao-adversarial/SKILL.md"
SKILL_SEM_FONTE = ".claude/skills/so-daqui/SKILL.md"
MODULO_DE_MENTIRA = "mod"
INSTRUMENTO_DE_MODULO = ".agents/mod/mod.py"
CARTAO_DE_EXECUCOES = "execucoes/LEIAME.md"
TERRITORIO_DE_MODULO = "conhecimento/mod/nota.md"
PAGINA_LIVRE = "conhecimento/livre.md"
INSTRUCOES_COM_MARCA = "AGENTS.md"
FONTE_DAS_INSTRUCOES = "nucleo/regras.json e nucleo/vocabulario.json"
MARCA_DAS_INSTRUCOES = (
    "<!-- GERADO de nucleo/regras.json e nucleo/vocabulario.json pelo "
    "`montar.py --sincronizar`. Editar aqui se perde. -->\n")


def escrever_de_mentira(raiz: Path, rel: str, texto: str = "corpo\n") -> None:
    alvo = raiz / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(texto, encoding="utf-8")


def montar_arvore_de_mentira(pasta: Path) -> None:
    (pasta / ".git").mkdir(parents=True, exist_ok=True)
    escrever_de_mentira(pasta, f"{ORIGEM_SKILLS}/{SKILL_ESPELHADA}")
    escrever_de_mentira(pasta, f"{COPIA_SKILLS}/{SKILL_ESPELHADA}")
    escrever_de_mentira(pasta, SKILL_SEM_FONTE)
    for rel in (INSTRUMENTO_DE_MODULO, CARTAO_DE_EXECUCOES,
                TERRITORIO_DE_MODULO, CARTAO_DO_MODULO):
        escrever_de_mentira(pasta, rel)
        escrever_de_mentira(
            pasta, f"{PASTA_MODULOS}/{MODULO_DE_MENTIRA}/{rel}")
    escrever_de_mentira(pasta, PAGINA_LIVRE)
    escrever_de_mentira(pasta, INSTRUCOES_COM_MARCA, MARCA_DAS_INSTRUCOES)


def pedido_de_shell(comando: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


def pedido_de_escrita(ferramenta: str, caminho: str) -> dict:
    campo = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"tool_name": ferramenta, "tool_input": {campo: caminho}}


def pedido_de_leitura(caminho: str) -> dict:
    return {"tool_name": "Read", "tool_input": {"file_path": caminho}}


ESPELHO_NA_COPIA = f"{COPIA_SKILLS}/{SKILL_ESPELHADA}"
ESPELHO_NA_FONTE = f"{ORIGEM_SKILLS}/{SKILL_ESPELHADA}"

BARRA = [
    ("Write no espelho de skill", pedido_de_escrita("Write", ESPELHO_NA_COPIA)),
    ("Edit no instrumento que veio de módulo",
     pedido_de_escrita("Edit", INSTRUMENTO_DE_MODULO)),
    ("NotebookEdit na cópia de módulo fora de .agents",
     pedido_de_escrita("NotebookEdit", CARTAO_DE_EXECUCOES)),
    ("Edit no arquivo que abre com a marca de gerado",
     pedido_de_escrita("Edit", INSTRUCOES_COM_MARCA)),
    ("heredoc de interpretador que ESCREVE na cópia — a bandeira do "
     "shell é a mesma, e o alvo mora dentro do script",
     pedido_de_shell(
         "python3 - <<'PY'\nimport pathlib\n"
         f"p = pathlib.Path('{INSTRUMENTO_DE_MODULO}')\n"
         "p.write_text(p.read_text() + 'x')\nPY")),
    ("o mesmo por -c, sem heredoc",
     pedido_de_shell(
         f"python3 -c \"open('{INSTRUMENTO_DE_MODULO}','w').write('x')\"")),
    ("redirecionamento de shell para dentro do espelho",
     pedido_de_shell(f"echo novo > {ESPELHO_NA_COPIA}")),
    ("sed -i na cópia de módulo",
     pedido_de_shell(f"sed -i s/a/b/ {INSTRUMENTO_DE_MODULO}")),
    ("cp por cima da cópia de módulo",
     pedido_de_shell(f"cp outro.md {CARTAO_DE_EXECUCOES}")),
    ("cd antes da escrita, com o caminho relativo à pasta nova",
     pedido_de_shell(f"cd .agents && echo x > mod/mod.py")),
    ("Write em skill órfã, que só existe na cópia — o --sincronizar a apaga",
     pedido_de_escrita("Write", SKILL_SEM_FONTE)),
]

DEIXA_PASSAR = [
    ("Write na FONTE do espelho", pedido_de_escrita("Write", ESPELHO_NA_FONTE)),
    ("Write no território do repositório, que a sincronização não reescreve",
     pedido_de_escrita("Write", TERRITORIO_DE_MODULO)),
    ("Write no cartão do módulo, que não vira cópia",
     pedido_de_escrita("Write", CARTAO_DO_MODULO)),
    ("Write em página que não é cópia de ninguém",
     pedido_de_escrita("Write", PAGINA_LIVRE)),
    ("Read do espelho — ler a cópia é livre",
     pedido_de_leitura(ESPELHO_NA_COPIA)),
    ("cat da cópia de módulo pelo shell",
     pedido_de_shell(f"cat {INSTRUMENTO_DE_MODULO}")),
    ("interpretador que só LÊ a cópia continua livre — regra 8, ler é livre",
     pedido_de_shell(
         "python3 - <<'PY'\n"
         f"print(open('{INSTRUMENTO_DE_MODULO}').read())\nPY")),
    ("interpretador que só LÊ a cópia continua livre",
     pedido_de_shell(
         "python3 - <<'PY'\n"
         f"print(open('{INSTRUMENTO_DE_MODULO}').read())\n"
         "PY")),
    ("grep no espelho", pedido_de_shell(f"grep -n x {ESPELHO_NA_COPIA}")),
    ("git log, que não escreve em arquivo nenhum",
     pedido_de_shell("git log --oneline -3")),
]

DESTE_REPOSITORIO_BARRA = [
    (".claude/skills/verificacao-adversarial/SKILL.md", ".agents/skills/verificacao-adversarial/SKILL.md"),
    (".agents/encadeador/encadeador.py",
     "modulos/encadeador/.agents/encadeador/encadeador.py"),
    ("execucoes/LEIAME.md", "modulos/encadeador/execucoes/LEIAME.md"),
]
DESTE_REPOSITORIO_PASSA = (".agents/skills/verificacao-adversarial/SKILL.md",)

FALHA_FONTE_ERRADA = "BARRA [{}]: negou nomeando {!r}, e a fonte é {!r}"
FALHA_DESTE_REPOSITORIO = "BARRA [{}]: deixou passar neste repositório"
FALHA_LEITURA_DESTE_REPOSITORIO = "DEIXA_PASSAR [Read de {}]: barrou"


def gabarito_do_instalador(raiz: Path):
    import importlib.util
    origem = importlib.util.spec_from_file_location(
        "instalador", raiz / INSTALADOR)
    if origem is None or not (raiz / INSTALADOR).is_file():
        return None
    instalador = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(instalador)
    esperadas = set(instalador.espelhos_com_fonte(raiz))
    for arquivos in instalador.modulos_no_disco(raiz).values():
        esperadas.update(
            rotulo for rotulo in arquivos
            if not instalador.e_territorio_do_repositorio(rotulo)
            and (raiz / rotulo).is_file())
    return esperadas


def testar() -> int:
    import tempfile
    falhas, comportamento = [], []
    with tempfile.TemporaryDirectory(prefix="veto-copia-gerada-") as tmp:
        raiz = Path(tmp).resolve()
        montar_arvore_de_mentira(raiz)
        onde = str(raiz)

        for rotulo, pedido in BARRA:
            if not recusa_do_pedido(pedido, raiz, onde):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, pedido in DEIXA_PASSAR:
            if recusa := recusa_do_pedido(pedido, raiz, onde):
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, recusa[1]))

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        espelho = recusa_do_pedido(
            pedido_de_escrita("Write", ESPELHO_NA_COPIA), raiz, onde)
        caso("a recusa do espelho nomeia a fonte em .agents/skills",
             espelho and espelho[1] == ESPELHO_NA_FONTE)
        de_modulo = recusa_do_pedido(
            pedido_de_escrita("Edit", INSTRUMENTO_DE_MODULO), raiz, onde)
        caso("a recusa da cópia de módulo nomeia o caminho em modulos/",
             de_modulo and de_modulo[1]
             == f"{PASTA_MODULOS}/{MODULO_DE_MENTIRA}/{INSTRUMENTO_DE_MODULO}")
        marcado = recusa_do_pedido(
            pedido_de_escrita("Edit", INSTRUCOES_COM_MARCA), raiz, onde)
        caso("onde há marca, a fonte sai da própria marca",
             marcado and marcado[1] == FONTE_DAS_INSTRUCOES)
        caso("a recusa não carrega caminho absoluto",
             espelho and str(raiz) not in RECUSA.format(*espelho, espelho[1]))
        caso("quem não entende o pedido recusa, em vez de liberar",
             recusou_sem_entender(ValueError("entrada quebrada")))

        mensagem = (RECUSA.format("AGENTS.md", "nucleo/", "nucleo/")
                    + MANDA_GRAVAR.format(APRENDIZADO))
        caso("a recusa nomeia a regra 15, diz onde o valor certo mora e "
             "manda gravar o aprendizado em conhecimento/",
             "Regra 15" in mensagem and "montar.py" in mensagem
             and "regra 4" in mensagem and "`conhecimento/`" in mensagem
             and APRENDIZADO in mensagem)

    daqui = raiz_do_projeto_nunca_o_cwd()

    with tempfile.TemporaryDirectory(prefix="veto-instalacao-fresca-") as tmp:
        fresca = Path(tmp).resolve()
        (fresca / "arquivo-instalado.py").write_text("x\n", encoding="utf-8")
        (fresca / INSTALADOR).write_text(
            "MODULOS = {'mod': {'arquivo-instalado.py': 'x'}}\n"
            "def e_territorio_do_repositorio(caminho):\n"
            "    return False\n", encoding="utf-8")
        recusa_fresca = recusa_do_pedido(
            pedido_de_escrita("Write", "arquivo-instalado.py"),
            fresca, str(fresca))
        caso("instalação sem modulos/ no disco ainda barra a cópia, pelo "
             "MODULOS embutido no montar.py",
             recusa_fresca is not None)
        caso("a recusa da instalação fresca nomeia o módulo, não um "
             "caminho local inexistente",
             recusa_fresca and recusa_fresca[1]
             == f"{MARCA_DE_MODULO_INSTALADO}mod")
        if recusa_fresca:
            mensagem_fresca = (
                RECUSA_MODULO_INSTALADO.format(
                    recusa_fresca[0], "mod", "mod")
                + MANDA_GRAVAR.format(APRENDIZADO_MODULO_INSTALADO))
            caso("a recusa da instalação fresca não manda rodar "
                 "--sincronizar, que não existe fora do repositório atlas",
                 "--sincronizar" not in mensagem_fresca
                 and "--atualizar" in mensagem_fresca)

    daqui = raiz_do_projeto_nunca_o_cwd()
    for copia, fonte in DESTE_REPOSITORIO_BARRA:
        recusa = recusa_do_pedido(
            pedido_de_escrita("Write", copia), daqui, str(daqui))
        if not recusa:
            falhas.append(FALHA_DESTE_REPOSITORIO.format(copia))
        elif recusa[1] != fonte:
            falhas.append(FALHA_FONTE_ERRADA.format(copia, recusa[1], fonte))
        if recusa_do_pedido(pedido_de_leitura(copia), daqui, str(daqui)):
            falhas.append(FALHA_LEITURA_DESTE_REPOSITORIO.format(copia))
    for fonte in DESTE_REPOSITORIO_PASSA:
        if recusa := recusa_do_pedido(
                pedido_de_escrita("Write", fonte), daqui, str(daqui)):
            falhas.append(FALHA_DEIXA_PASSAR.format(fonte, recusa[1]))

    esperadas = gabarito_do_instalador(daqui)
    if esperadas is None:
        comportamento.append(
            (SEM_INSTALADOR.format(INSTALADOR, INSTALADOR), False))
    else:
        derivadas = set(copias_geradas(daqui))
        comportamento.append((
            DIVERGENCIA_COM_O_INSTALADOR.format(
                sorted(derivadas - esperadas) or "nada",
                INSTALADOR, sorted(esperadas - derivadas) or "nada"),
            derivadas == esperadas))

    falhas += [FALHA_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]
    for falha in falhas:
        print(LINHA_DE_FALHA.format(falha))
    total = len(BARRA) + len(DEIXA_PASSAR) + len(comportamento) \
        + len(DESTE_REPOSITORIO_BARRA) * 2 + len(DESTE_REPOSITORIO_PASSA)
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(
        total, len(BARRA) + len(DESTE_REPOSITORIO_BARRA),
        len(DEIXA_PASSAR) + len(DESTE_REPOSITORIO_BARRA)
        + len(DESTE_REPOSITORIO_PASSA), len(comportamento)))
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
