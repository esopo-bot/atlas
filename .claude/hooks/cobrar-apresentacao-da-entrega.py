import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DAS_BRANCHES = "branches"
CHAVE_DA_INTEGRACAO = "integracao"
CHAVE_DA_APRESENTACAO = "apresentacao"
CHAVE_DO_ENDERECO = "endereco"
CHAVE_DA_VOZ = "por_voz"
CHAVE_DO_TRANSCRITO = "transcript_path"
CHAVE_DO_INSTANTE = "timestamp"
MARCA_DE_UTC = "Z"
FUSO_UTC = "+00:00"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
MARCA_DE_PESQUISA_NO_AMBIENTE = "ATLAS_SO_LEITURA"
PREFIXO_DAS_FERRAMENTAS_DO_NAVEGADOR_DO_DONO = "mcp__claude-in-chrome__"
FERRAMENTAS_DE_SHELL = ("Bash", "PowerShell")
FERRAMENTAS_QUE_ESCREVEM = ("Write", "Edit", "NotebookEdit")
CAMPO_DO_COMANDO = "command"
VERBOS_DO_GIT_QUE_ESCREVEM = ("commit", "merge", "push", "rebase", "revert",
                              "cherry-pick", "reset", "am", "apply", "stash")
MARCA_DO_INSTRUMENTO_DE_VOZ = "falar.py"
COMANDO_DE_BUSCA_DA_INTEGRACAO = ["git", "fetch", "--quiet", "origin", "{}"]
COMANDO_DAS_MESCLAS_DESDE = [
    "git", "log", "--format=%H %ct", "--since=@{0}", "origin/{1}"]
COMANDO_DA_RAIZ_DO_REPOSITORIO = ["git", "rev-parse", "--show-toplevel"]
TEMPO_DO_GIT = 15
TEMPO_DA_REDE = 25
EVENTO_DE_PARADA = "Stop"
DECISAO_DE_BLOQUEAR = "block"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0
FALHA_ABERTA = 0
COBRANCA_ENTREGUE = 0
NAO_MEDIDO = None

COBRA = (
    "Regra 2 da camada: só é pronto o que um instrumento provou, e para "
    "entrega com interface o instrumento é o dono vendo a tela. O vizinho "
    "`{vizinho}` declara apresentação no cadastro e recebeu mescla desta "
    "sessão na integração `{integracao}` ({quantas} commit(s)), mas depois "
    "dela o transcript não tem {faltou}.\n"
    "A receita: abra `{endereco}` no navegador do dono (as ferramentas do "
    "navegador dele, nunca só o Playwright), troque para o perfil que a "
    "prova pede pelo login que a camada já sabe fazer, percorra o que foi "
    "entregue{voz}, e defenda por que pode ir a produção. Só então o relato "
    "escrito. Apresentação anunciada e não feita conta como falta.")
AVISO_QUE_NAO_SEGURA_A_PARADA_POR_APRESENTACAO = (
    "SÓ NO REGISTRO DE DEPURAÇÃO, sem bloqueio: com gente no terminal esta "
    "cobrança da apresentação não chega à conversa nem à tela, e a parada "
    "segue.\n\n")
FALTOU_NAVEGACAO = "uma navegação ao endereço declarado pelo navegador do dono"
FALTOU_VOZ = "a narração por voz (`falar.py`)"
FALTOU_OS_DOIS = FALTOU_NAVEGACAO + " nem " + FALTOU_VOZ
PEDE_VOZ = ", narrando cada tela por voz"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


RAZAO_DE_NAO_MEDIR = []
MOTIVO_TEMPO_ESGOTADO = "o comando estourou {}s"
MOTIVO_NAO_SUBIU = "o comando não subiu ({})"


def responde_sem_aparar(comando: list, raiz: Path, tempo: int):
    try:
        pronto = subprocess.run(comando, cwd=raiz, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=tempo)
    except subprocess.TimeoutExpired:
        RAZAO_DE_NAO_MEDIR.append(MOTIVO_TEMPO_ESGOTADO.format(tempo))
        return NAO_MEDIDO
    except (OSError, subprocess.SubprocessError) as falha:
        RAZAO_DE_NAO_MEDIR.append(
            MOTIVO_NAO_SUBIU.format(type(falha).__name__))
        return NAO_MEDIDO
    return pronto.returncode, pronto.stdout or ""


def responde(comando: list, raiz: Path, tempo: int):
    resposta = responde_sem_aparar(comando, raiz, tempo)
    if resposta is NAO_MEDIDO:
        return NAO_MEDIDO
    return resposta[0], resposta[1].strip()


def instante_da_linha(dado):
    marcado = dado.get(CHAVE_DO_INSTANTE) if isinstance(dado, dict) else None
    if not isinstance(marcado, str):
        return None
    try:
        return datetime.fromisoformat(
            marcado.replace(MARCA_DE_UTC, FUSO_UTC)).timestamp()
    except ValueError:
        return None


def blocos_de_ferramenta(dado):
    corpo = (dado.get("message") or {}).get("content") if isinstance(dado, dict) else None
    for bloco in corpo if isinstance(corpo, list) else []:
        if isinstance(bloco, dict) and bloco.get("name"):
            yield bloco


def linhas_do_transcrito(caminho):
    if not caminho:
        return
    try:
        with open(caminho, encoding="utf-8") as transcrito:
            for linha in transcrito:
                try:
                    yield json.loads(linha)
                except ValueError:
                    continue
    except OSError:
        return


def primeiro_instante_do_transcrito(linhas):
    for dado in linhas:
        instante = instante_da_linha(dado)
        if instante is not None:
            return instante
    return None


def caminhos_escritos(linhas, raiz: Path) -> set:
    escritos = set()
    for dado in linhas:
        for bloco in blocos_de_ferramenta(dado):
            if bloco.get("name") in FERRAMENTAS_QUE_ESCREVEM:
                alvo = (bloco.get("input") or {}).get("file_path")
                if alvo:
                    escritos.add(str(Path(alvo)))
            elif bloco.get("name") in FERRAMENTAS_DE_SHELL:
                comando = (bloco.get("input") or {}).get(CAMPO_DO_COMANDO)
                if isinstance(comando, str):
                    escritos |= pastas_de_vizinho_escritas_no_comando(comando, raiz)
    return escritos


def comando_que_escreve(comando: str) -> bool:
    palavras = comando.replace("\\", "/").split()
    return any(palavra in VERBOS_DO_GIT_QUE_ESCREVEM for palavra in palavras)


def pastas_de_vizinho_escritas_no_comando(comando: str, raiz: Path) -> set:
    if not comando_que_escreve(comando):
        return set()
    achados = set()
    marca = "projetos/"
    for pedaco in comando.replace("\\", "/").split():
        limpo = pedaco.strip("'\";=")
        if marca in limpo:
            nome = limpo.split(marca, 1)[1].split("/", 1)[0]
            if nome:
                achados.add(str(raiz / "projetos" / nome / "x"))
    return achados


def raiz_git_da_pasta(pasta: Path):
    while not pasta.is_dir():
        if pasta.parent == pasta:
            return None
        pasta = pasta.parent
    resposta = responde(COMANDO_DA_RAIZ_DO_REPOSITORIO, pasta, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0 or not resposta[1]:
        return None
    return Path(resposta[1]).resolve()


def vizinhos_tocados(escritos: set, raiz: Path) -> list:
    principal = raiz.resolve()
    pastas = {Path(caminho).parent for caminho in escritos}
    raizes = {achada for achada in map(raiz_git_da_pasta, pastas)
              if achada and achada != principal}
    return sorted(raizes)


def apresentacao_declarada(raiz: Path, vizinho: Path):
    try:
        dado = json.loads((raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    projetos = dado.get(CHAVE_DOS_PROJETOS) if isinstance(dado, dict) else None
    if not isinstance(projetos, dict):
        return None
    projeto = next((p for p in projetos.values() if isinstance(p, dict)
                    and p.get(CHAVE_DO_REPOSITORIO) == vizinho.name), None)
    if projeto is None:
        return None
    return apresentacao_do_cadastro(projeto, dado.get(CHAVE_DAS_BRANCHES))


def apresentacao_do_cadastro(projeto: dict, branches_da_raiz):
    declarada = projeto.get(CHAVE_DA_APRESENTACAO)
    if not isinstance(declarada, dict):
        return None
    endereco = str(declarada.get(CHAVE_DO_ENDERECO) or "").strip()
    if not endereco:
        return None
    do_projeto = projeto.get(CHAVE_DAS_BRANCHES)
    integracao = ((do_projeto.get(CHAVE_DA_INTEGRACAO)
                   if isinstance(do_projeto, dict) else None)
                  or (branches_da_raiz.get(CHAVE_DA_INTEGRACAO)
                      if isinstance(branches_da_raiz, dict) else None))
    return {"endereco": endereco,
            "por_voz": bool(declarada.get(CHAVE_DA_VOZ)),
            "integracao": str(integracao).strip() if integracao else ""}


def mesclas_desta_sessao(vizinho: Path, integracao: str, abertura):
    if not integracao or abertura is None:
        return []
    responde([parte.format(integracao) for parte in COMANDO_DE_BUSCA_DA_INTEGRACAO],
             vizinho, TEMPO_DA_REDE)
    resposta = responde(
        [parte.format(int(abertura), integracao) for parte in COMANDO_DAS_MESCLAS_DESDE],
        vizinho, TEMPO_DO_GIT)
    if resposta is NAO_MEDIDO or resposta[0] != 0:
        return NAO_MEDIDO
    mesclas = []
    for linha in resposta[1].split("\n"):
        partes = linha.split()
        if len(partes) == 2 and partes[1].isdigit():
            mesclas.append((partes[0], int(partes[1])))
    return mesclas


def apresentacao_no_transcrito(linhas, endereco: str, depois_de: float) -> dict:
    visto = {"navegou": False, "falou": False}
    for dado in linhas:
        instante = instante_da_linha(dado)
        if instante is None or instante < depois_de:
            continue
        for bloco in blocos_de_ferramenta(dado):
            nome = str(bloco.get("name"))
            entrada = json.dumps(bloco.get("input") or {}, ensure_ascii=False)
            if nome.startswith(PREFIXO_DAS_FERRAMENTAS_DO_NAVEGADOR_DO_DONO) \
                    and endereco in entrada:
                visto["navegou"] = True
            elif nome in FERRAMENTAS_DE_SHELL and MARCA_DO_INSTRUMENTO_DE_VOZ in entrada:
                visto["falou"] = True
    return visto


def o_que_faltou(declarada: dict, visto: dict) -> str:
    falta_voz = declarada["por_voz"] and not visto["falou"]
    if not visto["navegou"] and falta_voz:
        return FALTOU_OS_DOIS
    if not visto["navegou"]:
        return FALTOU_NAVEGACAO
    if falta_voz:
        return FALTOU_VOZ
    return ""


def cobranca(vizinho: str, declarada: dict, mesclas: list, visto: dict) -> str:
    faltou = o_que_faltou(declarada, visto)
    if not faltou or not mesclas:
        return ""
    return COBRA.format(vizinho=vizinho, integracao=declarada["integracao"],
                        quantas=len(mesclas), faltou=faltou,
                        endereco=declarada["endereco"],
                        voz=PEDE_VOZ if declarada["por_voz"] else "")


def decisao(entrada: dict, raiz: Path) -> str:
    if os.environ.get(MARCA_DE_ETAPA_NO_AMBIENTE) or os.environ.get(MARCA_DE_PESQUISA_NO_AMBIENTE):
        return ""
    caminho = entrada.get(CHAVE_DO_TRANSCRITO)
    linhas = list(linhas_do_transcrito(caminho))
    abertura = primeiro_instante_do_transcrito(linhas)
    cobrancas = []
    for vizinho in vizinhos_tocados(caminhos_escritos(linhas, raiz), raiz):
        declarada = apresentacao_declarada(raiz, vizinho)
        if declarada is None:
            continue
        mesclas = mesclas_desta_sessao(vizinho, declarada["integracao"], abertura)
        if not mesclas:
            continue
        ultima = max(instante for _, instante in mesclas)
        visto = apresentacao_no_transcrito(linhas, declarada["endereco"], ultima)
        dito = cobranca(vizinho.name, declarada, mesclas, visto)
        if dito:
            cobrancas.append(dito)
    return "\n\n".join(cobrancas)


def escrever_fora_da_conversa(texto: str) -> None:
    sys.stdout.buffer.write((texto + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return SILENCIO
        motivo = decisao(entrada, raiz_do_projeto_nunca_o_cwd())
        if not motivo:
            return SILENCIO
    except Exception:
        return FALHA_ABERTA

    escrever_fora_da_conversa(
        AVISO_QUE_NAO_SEGURA_A_PARADA_POR_APRESENTACAO + motivo)
    return COBRANCA_ENTREGUE


def linha_de_transcrito(instante: str, nome: str, entrada: dict) -> dict:
    return {CHAVE_DO_INSTANTE: instante,
            "message": {"content": [{"type": "tool_use", "name": nome,
                                     "input": entrada}]}}


VIZINHO_DE_MENTIRA = Path("vizinho-x")
MARCAS_QUE_MUDAM_A_PARADA = (MARCA_DE_ETAPA_NO_AMBIENTE,
                             MARCA_DE_PESQUISA_NO_AMBIENTE)


def o_que_o_gancho_imprime(declarada: dict, mesclas: list, etapa: str = "",
                           codificacao: str = "utf-8") -> str:
    global vizinhos_tocados, apresentacao_declarada, mesclas_desta_sessao
    de_verdade = (vizinhos_tocados, apresentacao_declarada,
                  mesclas_desta_sessao, sys.stdin)
    ambiente_de_verdade = {marca: os.environ.pop(marca, None)
                           for marca in MARCAS_QUE_MUDAM_A_PARADA}
    impresso = io.TextIOWrapper(io.BytesIO(), encoding=codificacao)
    try:
        vizinhos_tocados = lambda escritos, raiz: [VIZINHO_DE_MENTIRA]
        apresentacao_declarada = lambda raiz, vizinho: declarada
        mesclas_desta_sessao = lambda vizinho, integracao, abertura: mesclas
        sys.stdin = io.StringIO("{}")
        if etapa:
            os.environ[MARCA_DE_ETAPA_NO_AMBIENTE] = etapa
        with contextlib.redirect_stdout(impresso):
            main()
        impresso.flush()
    finally:
        (vizinhos_tocados, apresentacao_declarada, mesclas_desta_sessao,
         sys.stdin) = de_verdade
        for marca, valor in ambiente_de_verdade.items():
            if valor is None:
                os.environ.pop(marca, None)
            else:
                os.environ[marca] = valor
    return impresso.buffer.getvalue().decode("utf-8")


INTEGRACAO_DE_MENTIRA = "homolog"
ABERTURA_DE_MENTIRA = "2020-01-01T00:00:00Z"


def git_de_mentira(arvore: Path, *argumentos) -> None:
    subprocess.run(["git", *argumentos], cwd=arvore, check=True,
                   capture_output=True)


def raiz_com_vizinho_mesclado(pasta: Path, endereco: str) -> tuple:
    origem, raiz = pasta / "origem", pasta / "raiz"
    vizinho = raiz / "projetos" / VIZINHO_DE_MENTIRA.name
    origem.mkdir()
    git_de_mentira(origem, "init", "-q", "-b", INTEGRACAO_DE_MENTIRA)
    git_de_mentira(origem, "config", "user.email", "prova@exemplo")
    git_de_mentira(origem, "config", "user.name", "Prova")
    git_de_mentira(origem, "commit", "-q", "--allow-empty", "-m", "mescla")
    vizinho.parent.mkdir(parents=True)
    git_de_mentira(pasta, "clone", "-q", str(origem), str(vizinho))
    (raiz / ARQUIVO_EXECUTOR).parent.mkdir(parents=True)
    (raiz / ARQUIVO_EXECUTOR).write_text(json.dumps({CHAVE_DOS_PROJETOS: {
        VIZINHO_DE_MENTIRA.name: {
            CHAVE_DO_REPOSITORIO: VIZINHO_DE_MENTIRA.name,
            CHAVE_DA_APRESENTACAO: {CHAVE_DO_ENDERECO: endereco},
            CHAVE_DAS_BRANCHES: {CHAVE_DA_INTEGRACAO: INTEGRACAO_DE_MENTIRA}}}}),
        encoding="utf-8")
    transcrito = pasta / "transcrito.jsonl"
    transcrito.write_text(json.dumps(linha_de_transcrito(
        ABERTURA_DE_MENTIRA, "Write",
        {"file_path": str(vizinho / "tela.txt")})) + "\n", encoding="utf-8")
    return raiz, transcrito


def rodar_o_gancho_sobre_o_transcrito(raiz: Path, transcrito: Path):
    ambiente = {**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(raiz)}
    for marca in MARCAS_QUE_MUDAM_A_PARADA:
        ambiente.pop(marca, None)
    entrada = json.dumps({"hook_event_name": EVENTO_DE_PARADA,
                          "stop_hook_active": False,
                          CHAVE_DO_TRANSCRITO: str(transcrito)})
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=entrada, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=ambiente)


def testar() -> int:
    casos = []
    endereco = "https://homolog.exemplo.test"
    antes = "2026-01-01T10:00:00Z"
    depois = "2026-01-01T12:00:00Z"
    mescla = datetime.fromisoformat("2026-01-01T11:00:00+00:00").timestamp()
    navega = linha_de_transcrito(depois, "mcp__claude-in-chrome__navigate",
                                 {"url": endereco + "/tela"})
    navega_cedo = linha_de_transcrito(antes, "mcp__claude-in-chrome__navigate",
                                      {"url": endereco + "/tela"})
    fala = linha_de_transcrito(depois, "Bash",
                               {"command": "python .agents/voz/falar.py oi"})
    playwright = linha_de_transcrito(depois, "Bash",
                                     {"command": "node provar.cjs " + endereco})
    com_voz = {"endereco": endereco, "por_voz": True, "integracao": "homolog"}
    sem_voz = {"endereco": endereco, "por_voz": False, "integracao": "homolog"}
    uma_mescla = [("abc", int(mescla))]

    def caso(rotulo, condicao):
        casos.append((rotulo, bool(condicao)))

    caso("cadastro sem apresentacao cala: a camada nao inventa exigencia",
         apresentacao_do_cadastro({"repositorio": "x"}, {"integracao": "homolog"}) is None)
    caso("cadastro com apresentacao herda a integracao da raiz",
         apresentacao_do_cadastro({"repositorio": "x", "apresentacao": {"endereco": endereco}},
                                  {"integracao": "homolog"})["integracao"] == "homolog")
    caso("mescla sem navegacao nem voz cobra os dois",
         FALTOU_OS_DOIS in cobranca("x", com_voz, uma_mescla,
                                    apresentacao_no_transcrito([], endereco, mescla)))
    caso("navegacao ANTES da mescla nao conta: apresentou o que ainda nao existia",
         FALTOU_NAVEGACAO in cobranca("x", sem_voz, uma_mescla,
                                      apresentacao_no_transcrito([navega_cedo], endereco, mescla)))
    caso("playwright no shell nao e o navegador do dono",
         FALTOU_NAVEGACAO in cobranca("x", sem_voz, uma_mescla,
                                      apresentacao_no_transcrito([playwright], endereco, mescla)))
    caso("navegacao depois da mescla sem voz, quando o cadastro pede voz, cobra so a voz",
         cobranca("x", com_voz, uma_mescla,
                  apresentacao_no_transcrito([navega], endereco, mescla)).count(FALTOU_VOZ) == 1)
    caso("navegacao e voz depois da mescla calam",
         cobranca("x", com_voz, uma_mescla,
                  apresentacao_no_transcrito([navega, fala], endereco, mescla)) == "")
    caso("sem mescla desta sessao cala, mesmo sem apresentacao",
         cobranca("x", com_voz, [], {"navegou": False, "falou": False}) == "")
    caso("comando de shell que ESCREVE em projetos/<nome> aponta o vizinho",
         any("projetos" in c and "vizinho-x" in c for c in
             pastas_de_vizinho_escritas_no_comando(
                 "git -C D:/raiz/projetos/vizinho-x/ merge --no-ff frente",
                 Path("D:/raiz"))))
    caso("comando que so LE o vizinho nao aponta ninguem: ler nao e entregar",
         pastas_de_vizinho_escritas_no_comando(
             "grep -ril feedback D:/raiz/projetos/vizinho-x", Path("D:/raiz")) == set())
    caso("git de leitura no vizinho tambem nao aponta ninguem",
         pastas_de_vizinho_escritas_no_comando(
             "git -C D:/raiz/projetos/vizinho-x status --short", Path("D:/raiz")) == set())
    caso("push da branch de trabalho no vizinho aponta o vizinho",
         pastas_de_vizinho_escritas_no_comando(
             "git -C D:/raiz/projetos/vizinho-x push origin issue/9-x",
             Path("D:/raiz")) != set())
    caso("silenciar o erro nao e escrever: leitura com 2>/dev/null nao aponta",
         pastas_de_vizinho_escritas_no_comando(
             "grep -ril feedback D:/raiz/projetos/vizinho-x 2>/dev/null | head -40",
             Path("D:/raiz")) == set())
    caso("mandar a saida para o nada tambem nao aponta",
         pastas_de_vizinho_escritas_no_comando(
             "ls D:/raiz/projetos/vizinho-x >/dev/null", Path("D:/raiz")) == set())
    caso("a cobranca diz o endereco e a receita",
         endereco in cobranca("x", com_voz, uma_mescla, {"navegou": False, "falou": False})
         and "Regra 2" in cobranca("x", com_voz, uma_mescla, {"navegou": False, "falou": False}))

    def parece_json(texto: str) -> bool:
        limpo = texto.strip()
        return limpo.startswith("{") and limpo.endswith("}")

    esperada = cobranca(VIZINHO_DE_MENTIRA.name, com_voz, uma_mescla,
                        {"navegou": False, "falou": False})
    com_gente = o_que_o_gancho_imprime(com_voz, uma_mescla)
    caso("com gente, a cobranca sai como texto comum, fora da conversa: a "
         "saida nao e JSON e nao tem systemMessage",
         com_gente.strip() and not parece_json(com_gente)
         and "systemMessage" not in com_gente)
    caso("a cobranca sai como aviso e nao segura a parada: o motivo vai "
         "inteiro no texto, sem decision e sem block",
         "decision" not in com_gente and "block" not in com_gente
         and com_gente.startswith(
             AVISO_QUE_NAO_SEGURA_A_PARADA_POR_APRESENTACAO)
         and esperada in com_gente)
    caso("com a marca de etapa, a mesma cobranca cala como hoje: nada na "
         "saida",
         o_que_o_gancho_imprime(com_voz, uma_mescla, etapa="trabalhar") == "")
    fora_do_cp1252 = dict(com_voz, endereco=endereco + "/\U0001F680")
    caso("em maquina sem o modo UTF-8, endereco fora do cp1252 sai inteiro "
         "em UTF-8: o JSON escapava tudo para ASCII, o texto comum nao escapa",
         "\U0001F680" in o_que_o_gancho_imprime(
             fora_do_cp1252, uma_mescla, codificacao="cp1252"))
    with tempfile.TemporaryDirectory(prefix="cobrar-apresentacao-") as tmp:
        raiz, transcrito = raiz_com_vizinho_mesclado(Path(tmp).resolve(),
                                                     endereco)
        cobrado = rodar_o_gancho_sobre_o_transcrito(raiz, transcrito)
    caso("CODIGO REAL: com gente, o evento de parada na entrada e a mescla "
         "no vizinho sem apresentacao, o gancho sai com codigo 0 - na "
         "parada, 2 com saida que nao e JSON vira bloqueio, e 1 vira aviso "
         "de falha na tela",
         cobrado.returncode == 0
         and cobrado.stdout.startswith(
             AVISO_QUE_NAO_SEGURA_A_PARADA_POR_APRESENTACAO)
         and endereco in cobrado.stdout)

    falhas = [rotulo for rotulo, passou in casos if not passou]
    for rotulo, passou in casos:
        print(("ok   " if passou else "FALHA") + " " + rotulo)
    print(f"{len(casos) - len(falhas)} de {len(casos)} casos")
    return 1 if falhas else 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
