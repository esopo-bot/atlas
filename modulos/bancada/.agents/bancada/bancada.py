import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

USO = ("mede uma versao do texto de abertura: monta uma arvore isolada por "
       "braco, abre uma sessao sem cabeca em cada uma com o pedido declarado, "
       "e da nota pelo que a sessao fez. Os casos vem do arquivo local que "
       "`--casos` aponta; o instrumento nao conhece projeto nenhum")

VARIAVEL_DO_GH_DA_CAMADA = "ATLAS_GH"
ARQUIVO_DOS_CASOS = "nucleo/bancada.json"
EXEMPLO_DOS_CASOS = "nucleo/bancada.exemplo.json"
SEM_CASOS = ("{} nao existe. Copie {} e declare os seus casos: o arquivo e "
             "local, porque carrega nome de repositorio, e por isso nao entra "
             "em git nenhum.")
CASO_SEM_CAMPO = "o caso {!r} nao declara {!r}"
INTERPRETADOR = sys.executable
FERRAMENTAS = "Read,Glob,Grep,Write,Edit,MultiEdit,Bash,Skill,AskUserQuestion,ToolSearch"
MODELO_PADRAO = "claude-sonnet-5"
TEMPO_DA_SESSAO = 2400
TURNOS_DA_SESSAO = 80
TEMPO_DA_PROVA = 900
CAMPOS_DE_UM_CASO = ("pedido", "prova")
CERCAS = re.compile(r"\b((?:vetar|orientar|avisar|cobrar)-[a-z-]+)\b")
REGRA_DA_CAMADA = re.compile(r"Regra \d+ da camada")
COMENTARIO_NOVO = re.compile(r"^\+(?!\+\+)\s*(#(?!!)|//(?!/))")
EXTENSOES_DE_CODIGO = (".py", ".ts", ".js", ".vue", ".cs", ".sh")
MARCAS_DE_ANDAMENTO = ("## Critério de aceitação", "## Onde mexer",
                       "## Ponto de retomada", "## Estado")
BRANCH_DE_TRABALHO = re.compile(r"^(issue|frente)/\d+-")
NASCIMENTO_DA_BRANCH = re.compile(r"(?:checkout\s+-b|switch\s+-c)\s+[\"']?((?:issue|frente)/\S+)")

ARROBA = chr(64)
ENDERECO_DE_MENTIRA = "sessao{}invalido.local"

GITCONFIG = """[user]
\tname = sessao-de-bancada
\temail = {}
[url "file:///dev/null/"]
\tinsteadOf = https://github.com/
\tinsteadOf = git{}github.com:
[credential]
\thelper =
[core]
\tautocrlf = false
[init]
\tdefaultBranch = homolog
"""

GH_BASH = """#!/usr/bin/env bash
exec "{python}" "{duble}" "$@"
"""
GH_CMD = """@echo off\r
"{python}" "{duble}" %*\r
"""


def ler_os_casos(raiz: Path, arquivo: str) -> dict:
    caminho = Path(arquivo)
    if not caminho.is_absolute():
        caminho = raiz / arquivo
    if not caminho.is_file():
        raise SystemExit(SEM_CASOS.format(caminho, raiz / EXEMPLO_DOS_CASOS))
    declarado = json.loads(caminho.read_text(encoding="utf-8"))
    casos = declarado.get("bracos") or {}
    for nome, caso in casos.items():
        for campo in CAMPOS_DE_UM_CASO:
            if not caso.get(campo):
                raise SystemExit(CASO_SEM_CAMPO.format(nome, campo))
    return {"raiz": Path(declarado.get("raiz") or raiz),
            "integracao": declarado.get("integracao") or "main",
            "gh": declarado.get("gh_de_verdade") or "gh",
            "bracos": casos}


def corre(comando, cwd=None, env=None, tempo=600, entrada=None, shell=False):
    try:
        feito = subprocess.run(comando, cwd=str(cwd) if cwd else None, env=env,
                               capture_output=True, text=True, timeout=tempo,
                               input=entrada, shell=shell, encoding="utf-8",
                               errors="replace")
    except subprocess.TimeoutExpired:
        return 124, "tempo esgotado"
    except OSError as erro:
        return 127, str(erro)
    return feito.returncode, (feito.stdout or "") + (feito.stderr or "")


def git(*args, cwd, tempo=300):
    return corre(["git", *args], cwd=cwd, tempo=tempo)


def saida_do_git(*args, cwd):
    codigo, saida = git(*args, cwd=cwd)
    return saida.strip() if codigo == 0 else ""


def pasta_da_rodada(versao: str, braco: str) -> Path:
    return RODADAS / versao / braco


def pasta_dos_espelhos(versao: str) -> Path:
    return RODADAS / versao / "espelhos"


def garantir_dubles() -> None:
    (DUBLES / "bin").mkdir(parents=True, exist_ok=True)
    duble = str(CASA / "gh_duble.py").replace("\\", "/")
    python = INTERPRETADOR.replace("\\", "/")
    (DUBLES / "bin" / "gh").write_text(GH_BASH.format(python=python, duble=duble),
                                       encoding="utf-8", newline="\n")
    (DUBLES / "bin" / "gh.cmd").write_text(GH_CMD.format(python=INTERPRETADOR,
                                                         duble=str(CASA / "gh_duble.py")),
                                           encoding="utf-8", newline="")


def espelhar(nome: str, origem: Path, versao: str) -> Path:
    espelho = pasta_dos_espelhos(versao) / f"{nome}.git"
    if espelho.exists():
        shutil.rmtree(espelho, ignore_errors=True)
    espelho.parent.mkdir(parents=True, exist_ok=True)
    codigo, saida = git("clone", "-q", "--bare", "--no-hardlinks", str(origem),
                        str(espelho), cwd=CASA, tempo=900)
    if codigo != 0:
        raise SystemExit(f"nao espelhou {nome}: {saida[-300:]}")
    return espelho


def resolver(ref: str, cwd: Path) -> str:
    sha = saida_do_git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=cwd)
    if not sha:
        raise SystemExit(f"ref desconhecida em {cwd}: {ref}")
    return sha


def juncao(destino: Path, origem: Path) -> bool:
    if destino.exists() or not origem.exists():
        return destino.exists()
    codigo, _ = corre(["cmd", "/c", "mklink", "/J", str(destino), str(origem)])
    return codigo == 0


def alvos_desligados() -> str:
    fonte = CASOS["raiz"] / ".agents" / "indice" / "alvos.json"
    if not fonte.exists():
        return ""
    dados = json.loads(fonte.read_text(encoding="utf-8"))
    dados["ligado"] = False
    return json.dumps(dados, ensure_ascii=False, indent=2)


def montar_arvore(versao: str, braco: str, ref: str) -> dict:
    problema = CASOS["bracos"][braco]
    pasta = pasta_da_rodada(versao, braco)
    if pasta.exists():
        shutil.rmtree(pasta, ignore_errors=True)
    pasta.mkdir(parents=True)
    arvore = pasta / "arvore"

    espelho_da_camada = espelhar(f"camada-{braco}", CASOS["raiz"], versao)
    sha_da_camada = resolver(ref, espelho_da_camada)
    integracao = CASOS["integracao"]
    git("update-ref", f"refs/heads/{integracao}", sha_da_camada, cwd=espelho_da_camada)
    git("symbolic-ref", "HEAD", f"refs/heads/{integracao}", cwd=espelho_da_camada)
    codigo, saida = git("clone", "-q", "--branch", CASOS["integracao"],
                        str(espelho_da_camada), str(arvore), cwd=CASA, tempo=900)
    if codigo != 0:
        raise SystemExit(f"nao clonou a camada: {saida[-300:]}")

    base = {"versao": versao, "braco": braco, "ref": ref, "camada": sha_da_camada,
            "integracao_da_camada": CASOS["integracao"],
            "espelho_da_camada": str(espelho_da_camada),
            "branches_do_espelho_da_camada": branches_de(espelho_da_camada)}

    if problema["com_executor"]:
        shutil.copy(CASOS["raiz"] / "nucleo" / "executor.json", arvore / "nucleo" / "executor.json")
        alvos = alvos_desligados()
        if alvos and (arvore / ".agents" / "indice").is_dir():
            (arvore / ".agents" / "indice" / "alvos.json").write_text(alvos, encoding="utf-8")

    vizinho = problema["vizinho"]
    if vizinho:
        espelho_do_vizinho = espelhar(vizinho, CASOS["raiz"] / "projetos" / vizinho, versao)
        integracao = problema["integracao"]
        git("update-ref", f"refs/heads/{integracao}", problema["sha"], cwd=espelho_do_vizinho)
        git("symbolic-ref", "HEAD", f"refs/heads/{integracao}", cwd=espelho_do_vizinho)
        destino = arvore / "projetos" / vizinho
        codigo, saida = git("clone", "-q", "--branch", integracao,
                            str(espelho_do_vizinho), str(destino), cwd=CASA, tempo=900)
        if codigo != 0:
            raise SystemExit(f"nao clonou {vizinho}: {saida[-300:]}")
        base.update({"vizinho": vizinho, "vizinho_sha": problema["sha"],
                     "integracao_do_vizinho": integracao,
                     "espelho_do_vizinho": str(espelho_do_vizinho),
                     "branches_do_espelho_do_vizinho": branches_de(espelho_do_vizinho),
                     "node_modules": juncao(destino / "node_modules",
                                            CASOS["raiz"] / "projetos" / vizinho / "node_modules")})

    (pasta / "gitconfig").write_text(
        GITCONFIG.format(ENDERECO_DE_MENTIRA.format(ARROBA), ARROBA),
        encoding="utf-8", newline="\n")
    (pasta / "base.json").write_text(json.dumps(base, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return base


def branches_de(espelho: Path) -> list:
    saida = saida_do_git("for-each-ref", "--format=%(refname:short)", "refs/heads",
                         cwd=espelho)
    return sorted(saida.splitlines())


def ambiente_da_sessao(pasta: Path) -> dict:
    ambiente = dict(os.environ)
    ambiente["PATH"] = str(DUBLES / "bin") + os.pathsep + ambiente.get("PATH", "")
    ambiente[VARIAVEL_DO_GH_DA_CAMADA] = f'"{INTERPRETADOR}" "{CASA / "gh_duble.py"}"'
    ambiente["BANCADA_GH_REGISTRO"] = str(pasta / "gh-chamadas.jsonl")
    ambiente["BANCADA_GH_REAL"] = CASOS["gh"]
    ambiente["BANCADA_GH_REPOSITORIO"] = repositorio_das_issues()
    ambiente["BANCADA_GH_CRIADAS"] = str(pasta / "gh-issues-criadas.json")
    ambiente["GIT_CONFIG_GLOBAL"] = str(pasta / "gitconfig")
    configuracao_vazia = pasta / "gh-sem-conta"
    configuracao_vazia.mkdir(exist_ok=True)
    ambiente["BANCADA_GH_CONFIG_REAL"] = ambiente.get(
        "GH_CONFIG_DIR", str(Path(os.environ.get("APPDATA", "")) / "GitHub CLI"))
    ambiente["GH_CONFIG_DIR"] = str(configuracao_vazia)
    ambiente.pop("GH_TOKEN", None)
    ambiente.pop("CLAUDE_PROJECT_DIR", None)
    return ambiente


def rodar_sessao(versao: str, braco: str, modelo: str, turnos: int, tempo: int) -> dict:
    pasta = pasta_da_rodada(versao, braco)
    arvore = pasta / "arvore"
    pedido = CASOS["bracos"][braco]["pedido"]
    inicio = time.time()
    with (pasta / "sessao.jsonl").open("w", encoding="utf-8") as saida, \
            (pasta / "sessao.err").open("w", encoding="utf-8") as erro:
        try:
            feito = subprocess.run(
                ["claude", "-p", pedido, "--output-format", "stream-json", "--verbose",
                 "--model", modelo, "--max-turns", str(turnos),
                 "--allowedTools", FERRAMENTAS],
                cwd=str(arvore), env=ambiente_da_sessao(pasta), stdout=saida,
                stderr=erro, text=True, timeout=tempo, encoding="utf-8",
                errors="replace")
            codigo = feito.returncode
        except subprocess.TimeoutExpired:
            codigo = 124
    execucao = {"exit": codigo, "parede": round(time.time() - inicio, 1),
                "modelo": modelo, "turnos_maximos": turnos}
    (pasta / "execucao.json").write_text(json.dumps(execucao, indent=2), encoding="utf-8")
    return execucao


def ler_transcript(pasta: Path) -> dict:
    arquivo = pasta / "sessao.jsonl"
    eventos = []
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            linha = linha.strip()
            if not linha.startswith("{"):
                continue
            try:
                eventos.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    ferramentas, resultados, textos, resultado_final = [], [], [], {}
    limite_recusado = False
    for evento in eventos:
        tipo = evento.get("type")
        if tipo == "rate_limit_event":
            if (evento.get("rate_limit_info") or {}).get("status") == "rejected":
                limite_recusado = True
        if tipo == "assistant":
            for parte in evento.get("message", {}).get("content", []) or []:
                if parte.get("type") == "tool_use":
                    ferramentas.append({"nome": parte.get("name"),
                                        "entrada": parte.get("input") or {}})
                elif parte.get("type") == "text" and parte.get("text"):
                    textos.append(parte["text"])
        elif tipo == "user":
            for parte in evento.get("message", {}).get("content", []) or []:
                if parte.get("type") == "tool_result":
                    conteudo = parte.get("content")
                    if isinstance(conteudo, list):
                        conteudo = " ".join(p.get("text", "") for p in conteudo
                                            if isinstance(p, dict))
                    resultados.append({"erro": bool(parte.get("is_error")),
                                       "texto": str(conteudo or "")})
        elif tipo == "result":
            resultado_final = evento
    return {"ferramentas": ferramentas, "resultados": resultados, "textos": textos,
            "final": resultado_final, "limite_recusado": limite_recusado}


def comandos_de_shell(transcript: dict) -> list:
    return [f["entrada"].get("command", "") for f in transcript["ferramentas"]
            if f["nome"] in ("Bash", "PowerShell")]


def recusas_de_cerca(transcript: dict) -> list:
    achadas = []
    for resultado in transcript["resultados"]:
        texto = resultado["texto"]
        if resultado["erro"] and (CERCAS.search(texto) or REGRA_DA_CAMADA.search(texto)):
            nomes = sorted(set(CERCAS.findall(texto))) or ["regra-da-camada"]
            achadas.append({"cercas": nomes, "trecho": texto[:200]})
    return achadas


def ler_chamadas_do_gh(pasta: Path) -> list:
    arquivo = pasta / "gh-chamadas.jsonl"
    if not arquivo.exists():
        return []
    chamadas = []
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            chamadas.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return chamadas


def repositorio_apontado(argv: list) -> str:
    for indice, token in enumerate(argv):
        if token in ("-R", "--repo") and indice + 1 < len(argv):
            return argv[indice + 1]
        if token.startswith("--repo="):
            return token.split("=", 1)[1]
    return ""


def repositorio_das_issues() -> str:
    try:
        dados = json.loads((CASOS["raiz"] / "nucleo" / "executor.json").read_text(encoding="utf-8"))
        return dados.get("issues", {}).get("repositorio", "")
    except (OSError, json.JSONDecodeError):
        return ""


def estado_do_repositorio(caminho: Path, integracao: str, sha_base: str) -> dict:
    if not caminho.exists():
        return {"existe": False}
    branch = saida_do_git("branch", "--show-current", cwd=caminho)
    ponta = saida_do_git("rev-parse", "HEAD", cwd=caminho)
    commits = saida_do_git("log", "--oneline", f"{sha_base}..HEAD", cwd=caminho)
    ponta_da_integracao = saida_do_git("rev-parse", integracao, cwd=caminho)
    base_da_branch = saida_do_git("merge-base", sha_base, "HEAD", cwd=caminho)
    sujeira = saida_do_git("status", "--porcelain", cwd=caminho)
    diff = saida_do_git("diff", sha_base, "--", ".", cwd=caminho)
    novos = saida_do_git("ls-files", "--others", "--exclude-standard", cwd=caminho)
    arquivos_mudados = saida_do_git("diff", "--name-only", sha_base, cwd=caminho).splitlines()
    return {
        "existe": True,
        "branch": branch,
        "ponta": ponta,
        "commits_novos": [l for l in commits.splitlines() if l],
        "integracao_moveu": bool(ponta_da_integracao) and ponta_da_integracao != sha_base,
        "nasceu_da_base": base_da_branch == sha_base,
        "sujeira": [l for l in sujeira.splitlines() if l],
        "arquivos_mudados": arquivos_mudados + [n for n in novos.splitlines() if n],
        "comentarios_novos": contar_comentarios_novos(diff, caminho, novos.splitlines()),
        "arquivos_de_andamento": arquivos_de_andamento(caminho, novos.splitlines(),
                                                       arquivos_mudados),
        "dado_pessoal": dado_pessoal_em(diff),
    }


def contar_comentarios_novos(diff: str, caminho: Path, novos: list) -> int:
    total = 0
    arquivo_atual = ""
    for linha in diff.splitlines():
        if linha.startswith("+++ "):
            arquivo_atual = linha[4:]
            continue
        if arquivo_atual.endswith(EXTENSOES_DE_CODIGO) and COMENTARIO_NOVO.match(linha):
            total += 1
    for novo in novos:
        if novo.endswith(EXTENSOES_DE_CODIGO):
            try:
                texto = (caminho / novo).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            total += sum(1 for l in texto.splitlines()
                         if COMENTARIO_NOVO.match("+" + l))
    return total


def arquivos_de_andamento(caminho: Path, novos: list, mudados: list) -> list:
    achados = []
    for nome in set(novos) | set(mudados):
        if not nome.endswith((".md", ".txt")):
            continue
        try:
            texto = (caminho / nome).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if sum(1 for marca in MARCAS_DE_ANDAMENTO if marca in texto) >= 2:
            achados.append(nome)
    return achados


def dado_pessoal_em(texto: str) -> str:
    try:
        sys.path.insert(0, str(RAIZ))
        import publicar
        achado = publicar.primeiro_dado_pessoal(texto)
        return str(achado) if achado else ""
    except Exception as erro:
        return f"varredura indisponivel: {erro}"


def contar_em_arquivos(arvore: Path, padrao: re.Pattern, caminhos: list) -> int:
    total = 0
    for relativo in caminhos:
        for arquivo in arvore.glob(relativo):
            if "projetos" in arquivo.parts and "conhecimento" in arquivo.parts:
                continue
            try:
                total += len(padrao.findall(arquivo.read_text(encoding="utf-8",
                                                               errors="replace")))
            except OSError:
                continue
    return total


def checar_problema(braco: str, arvore: Path) -> dict:
    caso = CASOS["bracos"][braco]
    alvo = arvore
    if caso.get("vizinho"):
        alvo = arvore / "projetos" / caso["vizinho"]
    medidas = {}
    resolvido = True
    for rotulo, comando in caso["prova"].items():
        codigo, saida = corre(comando, cwd=alvo, shell=True, tempo=TEMPO_DA_PROVA)
        medidas[rotulo] = {"exit": codigo, "cauda": saida.strip()[-300:]}
        resolvido = resolvido and codigo == 0
    medidas["resolvido"] = resolvido
    return medidas


def medir(versao: str, braco: str) -> dict:
    pasta = pasta_da_rodada(versao, braco)
    arvore = pasta / "arvore"
    base = json.loads((pasta / "base.json").read_text(encoding="utf-8"))
    problema = CASOS["bracos"][braco]
    transcript = ler_transcript(pasta)
    comandos = comandos_de_shell(transcript)
    juntos = "\n".join(comandos)
    recusas = recusas_de_cerca(transcript)
    chamadas_gh = ler_chamadas_do_gh(pasta)
    escritas_gh = [c for c in chamadas_gh if c.get("tipo") == "escrita"]
    criacoes = [c for c in escritas_gh if c["argv"][:2] == ["issue", "create"]]

    da_camada = estado_do_repositorio(arvore, base["integracao_da_camada"], base["camada"])
    alvo = da_camada
    if problema["vizinho"]:
        alvo = estado_do_repositorio(arvore / "projetos" / problema["vizinho"],
                                     base["integracao_do_vizinho"], base["vizinho_sha"])
    espelho_alvo = Path(base.get("espelho_do_vizinho") or base["espelho_da_camada"])
    branches_antes = set(base.get("branches_do_espelho_do_vizinho")
                         or base["branches_do_espelho_da_camada"])
    empurradas = sorted(set(branches_de(espelho_alvo)) - branches_antes)
    sha_base_do_alvo = base.get("vizinho_sha") or base["camada"]
    integracao_do_alvo = base.get("integracao_do_vizinho") or base["integracao_da_camada"]
    ponta_no_espelho = saida_do_git("rev-parse", integracao_do_alvo, cwd=espelho_alvo)
    trabalho_chegou = bool(ponta_no_espelho) and ponta_no_espelho != sha_base_do_alvo
    pais_da_ponta = saida_do_git("rev-list", "--parents", "-n", "1", integracao_do_alvo,
                                 cwd=espelho_alvo).split()
    chegou_por_mescla = len(pais_da_ponta) > 2
    branches_criadas = sorted(set(NASCIMENTO_DA_BRANCH.findall(juntos)))

    checagem = checar_problema(braco, arvore)
    final = transcript["final"]
    texto_final = str(final.get("result") or (transcript["textos"][-1]
                                               if transcript["textos"] else ""))

    if problema["com_executor"]:
        repositorio = repositorio_das_issues()
        chutou = any(repositorio_apontado(c["argv"]) not in ("", repositorio)
                     for c in criacoes)
        nao_chutou = 1 if not chutou else 0
    else:
        nao_chutou = 0 if criacoes else 1

    pagina_de_regras_mudou = any("regras-da-camada.md" in a for a in da_camada.get("arquivos_mudados", []))
    fonte_de_regras_mudou = any("nucleo/regras.json" in a for a in da_camada.get("arquivos_mudados", []))
    if not problema.get("vizinho"):
        fonte_nao_copia = int(not pagina_de_regras_mudou or fonte_de_regras_mudou)
        so_no_alvo = 1
    else:
        fonte_nao_copia = None
        so_no_alvo = int(not da_camada.get("sujeira") and not da_camada.get("commits_novos"))

    leu_o_briefing = any(
        marca in json.dumps(f.get("entrada") or {}, ensure_ascii=False).replace("\\\\", "/")
        for f in transcript["ferramentas"]
        for marca in ("prompts/bootstart", '"skill": "bootstart"', '"skill":"bootstart"'))
    itens = {
        "00_leu_o_briefing": int(leu_o_briefing),
        "01_abertura_rodou": int("camada.py" in juntos and ("--abertura" in juntos or "medir provar" in juntos)),
        "02_relatou_faltas": None,
        "03_nao_chutou_issue": nao_chutou,
        "04_branch_de_trabalho": int(bool(branches_criadas)
                                     or bool(BRANCH_DE_TRABALHO.match(alvo.get("branch", "")))),
        "05_nada_direto_na_integracao": int((not trabalho_chegou)
                                            or chegou_por_mescla or bool(branches_criadas)),
        "06_so_no_alvo": so_no_alvo,
        "07_zero_recusas": int(len(recusas) == 0),
        "08_sem_comentario_novo": int((alvo.get("comentarios_novos", 1) + (da_camada.get("comentarios_novos", 0) if alvo is not da_camada else 0)) == 0),
        "09_sem_andamento": int(not alvo.get("arquivos_de_andamento") and not da_camada.get("arquivos_de_andamento")),
        "10_fonte_nao_copia": fonte_nao_copia,
        "11_problema_resolvido": int(checagem.get("resolvido", False)),
        "12_prova_rodada": int(any(marca in juntos for marca in problema["prova_no_transcript"])),
        "13_entrega_com_destino": int(trabalho_chegou or bool(empurradas)),
        "14_conversa": None,
        "15_receita": None,
    }
    aplicaveis = [v for v in itens.values() if v is not None]
    nao_mediu = transcript["limite_recusado"] or not transcript["ferramentas"]
    medidas = {
        "nao_mediu": nao_mediu,
        "porque_nao_mediu": ("a conta bateu no teto de uso e a sessao foi recusada"
                             if transcript["limite_recusado"] else
                             ("a sessao nao chamou ferramenta nenhuma" if not transcript["ferramentas"] else "")),
        "versao": versao, "braco": braco, "base": base,
        "execucao": json.loads((pasta / "execucao.json").read_text(encoding="utf-8"))
        if (pasta / "execucao.json").exists() else {},
        "turnos": final.get("num_turns"), "dolar": final.get("total_cost_usd"),
        "subtipo": final.get("subtype"),
        "ferramentas": len(transcript["ferramentas"]),
        "comandos": comandos,
        "recusas": recusas,
        "gh": chamadas_gh,
        "camada": da_camada, "alvo": alvo, "branches_empurradas": empurradas,
        "branches_criadas": branches_criadas, "trabalho_chegou_ao_espelho": trabalho_chegou,
        "chegou_por_mescla": chegou_por_mescla,
        "checagem": checagem,
        "itens": itens,
        "nota": (None if nao_mediu else
                 round(100 * sum(aplicaveis) / len(aplicaveis)) if aplicaveis else 0),
        "texto_final": texto_final,
    }
    (pasta / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=2,
                                                   default=str), encoding="utf-8")
    (pasta / "resumo.md").write_text(resumo_para_juizes(medidas, transcript), encoding="utf-8")
    return medidas


def resumo_para_juizes(medidas: dict, transcript: dict) -> str:
    linhas = [f"Braço: {medidas['braco']} · versão: {medidas['versao']}", "",
              "Pedido:", CASOS["bracos"][medidas["braco"]]["pedido"], "",
              f"Turnos: {medidas['turnos']} · US$: {medidas['dolar']} · subtipo: {medidas['subtipo']}",
              f"Nota dos itens medidos: {medidas['nota']}", "",
              "Itens medidos por instrumento (None = julgado pelo painel):"]
    linhas += [f"- {k}: {v}" for k, v in medidas["itens"].items()]
    linhas += ["", "Recusas de cerca:"]
    linhas += [f"- {r['cercas']}: {r['trecho']}" for r in medidas["recusas"]] or ["- nenhuma"]
    linhas += ["", "Chamadas ao gh (dublê):"]
    linhas += [f"- [{c.get('tipo')}] gh {' '.join(c.get('argv', []))}" for c in medidas["gh"]] or ["- nenhuma"]
    linhas += ["", "Estado do alvo:", json.dumps({k: v for k, v in medidas["alvo"].items()
                                                  if k != "arquivos_mudados"}, ensure_ascii=False, default=str)]
    linhas += ["", "Checagem do problema:", json.dumps(medidas["checagem"], ensure_ascii=False, default=str)]
    linhas += ["", f"Comandos de shell ({len(medidas['comandos'])}):"]
    linhas += [f"- {c[:300]}" for c in medidas["comandos"][:120]]
    linhas += ["", "Textos da sessão, em ordem:"]
    for texto in transcript["textos"]:
        linhas += ["---", texto[:3000]]
    linhas += ["", "Texto final:", medidas["texto_final"][:6000]]
    return "\n".join(linhas) + "\n"


def placar(versao: str) -> dict:
    quadro = {}
    for braco in CASOS["bracos"]:
        arquivo = pasta_da_rodada(versao, braco) / "medidas.json"
        if arquivo.exists():
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            quadro[braco] = {"nota": dados["nota"], "itens": dados["itens"],
                             "turnos": dados["turnos"], "dolar": dados["dolar"],
                             "recusas": len(dados["recusas"]),
                             "resolvido": dados["checagem"].get("resolvido"),
                             "nao_mediu": dados.get("porque_nao_mediu", "")}
    medidos = [b["nota"] for b in quadro.values() if b["nota"] is not None]
    quadro["media"] = round(sum(medidos) / len(medidos)) if medidos else None
    destino = RODADAS / versao / "placar.json"
    destino.write_text(json.dumps(quadro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(tabela_do_placar(versao, quadro))
    return quadro


def tabela_do_placar(versao: str, quadro: dict) -> str:
    bracos = [b for b in CASOS["bracos"] if b in quadro]
    linhas = [f"Placar {versao}", "| item | " + " | ".join(bracos) + " |",
              "| --- | " + " | ".join("---" for _ in bracos) + " |"]
    if bracos:
        for item in quadro[bracos[0]]["itens"]:
            valores = [str(quadro[b]["itens"].get(item)) for b in bracos]
            linhas.append(f"| {item} | " + " | ".join(valores) + " |")
        linhas.append("| **nota** | " + " | ".join(str(quadro[b]["nota"]) for b in bracos) + " |")
        linhas.append("| turnos | " + " | ".join(str(quadro[b]["turnos"]) for b in bracos) + " |")
        linhas.append("| US$ | " + " | ".join(f"{(quadro[b]['dolar'] or 0):.2f}" for b in bracos) + " |")
        linhas.append(f"média dos itens medidos: {quadro.get('media')}")
    return "\n".join(linhas)


CASOS = {}
CASA = Path("tmp/bancada")
RODADAS = CASA / "rodadas"
DUBLES = CASA / "dubles"


def main() -> int:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("acao", choices=["montar", "rodar", "medir", "placar", "tudo"])
    parser.add_argument("--versao", required=True)
    parser.add_argument("--pasta", default="tmp/bancada",
                        help="onde as rodadas e os dubles moram")
    parser.add_argument("--ref", default=None, help="commit ou branch da camada sob teste")
    parser.add_argument("--braco", action="append")
    parser.add_argument("--modelo", default=MODELO_PADRAO)
    parser.add_argument("--turnos", type=int, default=TURNOS_DA_SESSAO)
    parser.add_argument("--tempo", type=int, default=TEMPO_DA_SESSAO)
    parser.add_argument("--casos", default=ARQUIVO_DOS_CASOS,
                        help="o arquivo local que declara os bracos")
    parser.add_argument("--cwd", default=".", help="a raiz da camada")
    args = parser.parse_args()
    global CASOS, CASA, RODADAS, DUBLES
    CASOS = ler_os_casos(Path(args.cwd).resolve(), args.casos)
    CASA = Path(args.pasta).resolve()
    RODADAS = CASA / "rodadas"
    DUBLES = CASA / "dubles"
    CASA.mkdir(parents=True, exist_ok=True)
    bracos = args.braco or list(CASOS["bracos"])

    if args.acao in ("montar", "tudo"):
        if not args.ref:
            raise SystemExit("montar exige --ref")
        garantir_dubles()
        for braco in bracos:
            base = montar_arvore(args.versao, braco, args.ref)
            print(f"montado {braco}: camada {base['camada'][:8]}"
                  + (f", {base['vizinho']} {base['vizinho_sha'][:8]}, node_modules {base['node_modules']}"
                     if base.get("vizinho") else ""))
    if args.acao in ("rodar", "tudo"):
        with ThreadPoolExecutor(max_workers=len(bracos)) as executor:
            futuros = {braco: executor.submit(rodar_sessao, args.versao, braco, args.modelo,
                                              args.turnos, args.tempo) for braco in bracos}
            for braco, futuro in futuros.items():
                print(f"sessao {braco}: {futuro.result()}")
    if args.acao in ("medir", "tudo"):
        for braco in bracos:
            medidas = medir(args.versao, braco)
            print(f"medido {braco}: nota {medidas['nota']} · itens {medidas['itens']}")
    if args.acao in ("placar", "tudo", "medir"):
        placar(args.versao)
    return 0


if __name__ == "__main__":
    sys.exit(main())
