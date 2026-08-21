import argparse
import ast
import contextlib
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DESCRICAO_DA_CLI = ("revisa a camada instalada neste repositório: o que ela "
                    "cobra de contexto, se os instrumentos se provam, e se "
                    "uma sessão de verdade lê e aplica as regras")

CARREGADOS_EM_TODA_SESSAO = ("AGENTS.md", "CLAUDE.md")
CONFIGURACOES_DO_CLAUDE = (".claude/settings.json",
                          ".claude/settings.local.json")
CHAVE_DOS_GANCHOS = "hooks"
EVENTO_DE_ABERTURA = "SessionStart"
CHAVE_DO_COMANDO = "command"
CHAVE_DA_SAIDA_DO_GANCHO = "hookSpecificOutput"
CHAVE_DO_CONTEXTO_INJETADO = "additionalContext"
RAIZ_NO_COMANDO = "${CLAUDE_PROJECT_DIR}"
RAIZ_NO_COMANDO_SEM_CHAVES = "$CLAUDE_PROJECT_DIR"
ENTRADA_VAZIA_DO_GANCHO = "{}"
TEMPO_DE_UM_GANCHO = 30
PASTA_DAS_SKILLS = ".claude/skills"
PASTA_DAS_SKILLS_FONTE = ".agents/skills"
PASTA_DOS_GANCHOS = ".claude/hooks"
PASTA_DOS_SUBAGENTES = ".claude/agents"
PASTA_DOS_INSTRUMENTOS = ".agents"
PASTA_DO_CONHECIMENTO = "conhecimento"
INSTALADOR = "montar.py"
INTERPRETADOR = sys.executable
INTERPRETADOR_NO_SHELL = f'"{sys.executable}"'
CANDIDATOS_DE_INTERPRETADOR = ("python3", "python", "py")
PERGUNTA_DA_VERSAO = "import sys; print(sys.version_info[0])"
VERSAO_QUE_SERVE = "3"
TETO_DO_INTERPRETADOR_S = 10
FONTE_DAS_REGRAS = "nucleo/regras.json"
FONTE_DO_VOCABULARIO = "nucleo/vocabulario.json"
FORA_DA_CONTA_DO_VOCABULARIO = ("nucleo/vocabulario.json", "montar.py")
TITULO_VOCABULARIO = "O VOCABULÁRIO, TERMO A TERMO"
TITULO_ENTREGA = "A ENTREGA — o que ainda não saiu da máquina"
TITULO_LARGADA = "A LARGADA — o que toda sessão paga antes de trabalhar"
ARQUIVO_DE_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DO_TETO = "teto_da_largada_em_bytes"
LARGADA_SEM_TETO = ("Largada: {} bytes. Sem teto declarado em {} ({}) — "
                    "medido, não cobrado.")
LARGADA_NA_REGUA = "Largada: {} bytes, dentro do teto de {}."
LARGADA_ACIMA = ("Largada: {} bytes, ACIMA do teto de {}. Cada byte "
                 "aqui é pago por toda sessão, antes de ela trabalhar: "
                 "corte página, skill ou gancho de abertura, ou mude o teto por decisão.")
COMANDO_DA_BRANCH = "git rev-parse --abbrev-ref HEAD"
COMANDO_DO_UPSTREAM = "git rev-parse --abbrev-ref --symbolic-full-name @{u}"
COMANDO_DO_ESPELHO = "git rev-parse --abbrev-ref origin/{}"
COMANDO_DO_QUE_FALTA = "git log {}..HEAD --oneline"
ENTREGA_LIMPA = "Nada ficou para trás: {} não tem commit fora de {}."
ENTREGA_COM_SOBRA = ("{} commit(s) em {} que NÃO estão em {} — trabalho "
                     "que fica para trás se a sessão acabar agora:")
SEM_ENTREGA = ("{} não tem para onde entregar — nem upstream declarado, "
               "nem origin/{} no remoto. Nada saiu da máquina, então "
               "não há como provar que nada ficou para trás.")
FORA_DE_REPOSITORIO = "Sem git aqui — nada a medir."
LINHA_DO_TERMO = "  {:<16} bruto {:>3}  exceção {:>3}  saldo {:>3}  {}"
TERMO_FECHADO = "ok"
TERMO_ABERTO = "ABERTO"
TERMO_NAO_MEDIDO = "NÃO MEDIDO"
TERMO_COM_FOLGA = "FOLGA {}"
SEM_MEDIDA = "-"
TETO_DE_ARGUMENTOS = 100000
GREP_ERROU_A_PARTIR_DE = 2
VOCABULARIO_NAO_MEDIDO = ("Vocabulário NÃO MEDIDO em {} termo(s): o grep falhou, "
                          "e falha não é zero.")
VOCABULARIO_FECHADO = "Vocabulário fechado: nenhum termo com saldo."
VOCABULARIO_COM_FOLGA = (
    "Vocabulário com {} exceção(ões) a mais do que existe no disco — a "
    "declaração envelheceu, e enquanto ela sobra o termo pode reabrir sem "
    "ninguém ver: a ocorrência nova entra no lugar da que sumiu. Meça e "
    "acerte o campo `ocorrencias` do termo.")
VOCABULARIO_ABERTO = ("Vocabulário com {} ocorrência(s) em aberto — o "
                      "termo velho voltou, ou a exceção declarada envelheceu.")
SEM_VOCABULARIO = "Sem {} — nada a medir."
RASCUNHO = "tmp"
GLOB_PYTHON = "*.py"
GLOB_SKILL = "*/SKILL.md"
GLOB_PAGINA = "*.md"
BANDEIRA_DE_TESTE = "--testar"
MARCAS_DE_RESUMO = ("OK:", "FALHOU:")

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
CAMPO_DESCRICAO = re.compile(r"^description:\s*(.+)$", re.M)
CAMPO_DAS_FERRAMENTAS = re.compile(r"^tools:\s*\S", re.M)
FORMAS_DE_FUNCAO = (ast.FunctionDef, ast.AsyncFunctionDef)
MARCA_DE_TESTE_NO_NOME = "test"
LINHA_DO_CATALOGO = "- {}: {}\n"

MODELO_DA_SIMULACAO = "claude-haiku-4-5-20251001"
FERRAMENTAS_DA_SIMULACAO = "Read,Glob,Grep,Write,Bash"
TEMPO_DA_SIMULACAO = 900
TEMPO_DE_UM_TESTE = 900
ARQUIVO_PEDIDO = "tmp/somar.py"

TITULO_MEDIR = "O QUE A CAMADA COBRA"
TITULO_PROVAR = "O QUE A CAMADA PROVA"
TITULO_SIMULAR = "UMA SESSÃO DE VERDADE"
LINHA = "  {:<44} {}"
LINHA_DE_CASO = "  [{}] {}"
SEM_CLAUDE = "  (claude fora do PATH — a simulação não rodou)"
SEM_REGRAS = "  (sem nucleo/regras.json — a simulação não tem gabarito)"
NUMERO_DESCONHECIDO = "Número que não existe: {}.\nOs que existem: {}."
FORA_DA_RAIZ = "Rode na raiz do repositório: {} não encontrado aqui."

PEDIDO = """Você abriu esta sessão na raiz de um repositório que tem uma camada de
instruções para agentes. Leia o que a camada manda ler e faça as duas coisas.

PARTE 1 — responda pelo que a camada diz, não pelo que você acha.
PARTE 2 — escreva o arquivo {arquivo}: um script que soma os inteiros passados na
linha de comando e imprime a soma. Ele precisa ter um `--testar` próprio que sai 0
quando passa, e esse teste tem de exercitar o código do próprio arquivo.

Sua ÚLTIMA mensagem tem de ser só este JSON, sem cerca de código:
{{"onde_abrir": "<em que pasta a sessão se abre e por quê>",
  "quantas_regras": <número inteiro de regras numeradas da camada>,
  "posso_commitar": "<sim|nao|depende — e em uma frase, por quê>",
  "segredo_em_texto_rastreado": "<o que a camada manda escrever no lugar do valor>",
  "branch_de_longa_duracao": "<o que a camada manda fazer com ela>",
  "o_que_e_pronto": "<quando a camada deixa chamar um trabalho de pronto>"}}"""


def corre(comando, tempo=TEMPO_DE_UM_TESTE):
    r = subprocess.run(comando, shell=True, capture_output=True, text=True,
                       timeout=tempo)
    return r.returncode, (r.stdout + r.stderr).strip()


def pasta_das_skills(raiz: Path) -> Path:
    instalada = raiz / PASTA_DAS_SKILLS
    return instalada if instalada.is_dir() else raiz / PASTA_DAS_SKILLS_FONTE


def catalogo_e_corpo(skill: Path) -> tuple:
    texto = skill.read_text(encoding="utf-8", errors="replace")
    frente = FRONTMATTER.match(texto)
    if not frente:
        return "", len(texto.encode())
    nome = CAMPO_NOME.search(frente.group(1))
    descricao = CAMPO_DESCRICAO.search(frente.group(1))
    if not (nome and descricao):
        return "", len(texto.encode())
    listada = LINHA_DO_CATALOGO.format(nome.group(1).strip(),
                                       descricao.group(1).strip())
    return listada, len(texto.encode()) - len(frente.group(1).encode())


@functools.lru_cache(maxsize=1)
def interpretador_com_nome_portatil() -> str:
    for nome in CANDIDATOS_DE_INTERPRETADOR:
        if not shutil.which(nome):
            continue
        try:
            pronto = subprocess.run(
                [nome, "-c", PERGUNTA_DA_VERSAO], capture_output=True,
                text=True, timeout=TETO_DO_INTERPRETADOR_S)
        except (OSError, subprocess.SubprocessError):
            continue
        if pronto.returncode == 0 and \
                pronto.stdout.strip() == VERSAO_QUE_SERVE:
            return nome
    return CANDIDATOS_DE_INTERPRETADOR[0]


def comandos_de_abertura(raiz: Path) -> list:
    comandos = []
    for nome in CONFIGURACOES_DO_CLAUDE:
        try:
            dado = json.loads(
                (raiz / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        blocos = (dado.get(CHAVE_DOS_GANCHOS) or {}).get(
            EVENTO_DE_ABERTURA) or []
        for bloco in blocos:
            for gancho in (bloco.get(CHAVE_DOS_GANCHOS) or []):
                if gancho.get(CHAVE_DO_COMANDO):
                    comandos.append(gancho[CHAVE_DO_COMANDO])
    return comandos


def bytes_que_os_ganchos_injetam(raiz: Path) -> tuple:
    total, cegos = 0, 0
    for comando in comandos_de_abertura(raiz):
        real = comando.replace(RAIZ_NO_COMANDO, str(raiz)).replace(
            RAIZ_NO_COMANDO_SEM_CHAVES, str(raiz))
        try:
            pronto = subprocess.run(
                real, shell=True, input=ENTRADA_VAZIA_DO_GANCHO,
                capture_output=True, text=True, cwd=raiz,
                timeout=TEMPO_DE_UM_GANCHO)
        except (OSError, subprocess.SubprocessError):
            cegos += 1
            continue
        if pronto.returncode != 0:
            cegos += 1
            continue
        with contextlib.suppress(ValueError, KeyError, TypeError,
                                 AttributeError):
            injetado = json.loads(pronto.stdout)[
                CHAVE_DA_SAIDA_DO_GANCHO][CHAVE_DO_CONTEXTO_INJETADO]
            total += len(injetado.encode())
    return total, cegos


def lotes_de_caminhos(alvos: list) -> list:
    lotes, atual, tamanho = [], [], 0
    for caminho in alvos:
        if atual and tamanho + len(caminho) > TETO_DE_ARGUMENTOS:
            lotes.append(atual)
            atual, tamanho = [], 0
        atual.append(caminho)
        tamanho += len(caminho) + 1
    if atual:
        lotes.append(atual)
    return lotes


def quantas_linhas_casam(padrao: str, alvos: list, raiz: Path):
    total = 0
    for lote in lotes_de_caminhos(alvos):
        try:
            pronto = subprocess.run(
                ["grep", "-cInP", padrao] + lote, cwd=raiz,
                capture_output=True, text=True,
                timeout=TEMPO_DE_UM_TESTE)
        except (OSError, subprocess.SubprocessError):
            return None
        if pronto.returncode >= GREP_ERROU_A_PARTIR_DE:
            return None
        with contextlib.suppress(ValueError, IndexError):
            total += sum(int(l.rsplit(":", 1)[1])
                         for l in pronto.stdout.split("\n") if l)
    return total


def saldo_do_vocabulario(raiz: Path) -> list:
    fonte = raiz / FONTE_DO_VOCABULARIO
    if not fonte.is_file():
        return []
    try:
        termos = json.loads(fonte.read_text(encoding="utf-8"))["termos"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    listados = corre(f'cd "{raiz}" && git ls-files')[1].split("\n")
    alvos = [c for c in listados
             if c and c not in FORA_DA_CONTA_DO_VOCABULARIO]
    if not alvos:
        return []
    contas = []
    for termo in termos:
        achadas = quantas_linhas_casam(
            termo["pronto"]["padrao"], alvos, raiz)
        perdoadas = sum(e.get("ocorrencias", 0)
                        for e in termo.get("excecoes", []))
        saldo = None if achadas is None else max(achadas - perdoadas, 0)
        contas.append((termo["id"], achadas, perdoadas, saldo))
    return contas


def folga_do_termo(bruto, perdoadas: int) -> int:
    return 0 if bruto is None else max(perdoadas - bruto, 0)


def vocabulario(raiz: Path) -> int:
    contas = saldo_do_vocabulario(raiz)
    if not contas:
        print(SEM_VOCABULARIO.format(FONTE_DO_VOCABULARIO))
        return 0
    print(f"\n{TITULO_VOCABULARIO}")
    for nome, bruto, perdoadas, saldo in contas:
        folga = folga_do_termo(bruto, perdoadas)
        print(LINHA_DO_TERMO.format(
            nome, SEM_MEDIDA if bruto is None else bruto, perdoadas,
            SEM_MEDIDA if saldo is None else saldo,
            TERMO_NAO_MEDIDO if saldo is None else
            (TERMO_ABERTO if saldo else
             (TERMO_COM_FOLGA.format(folga) if folga else TERMO_FECHADO))))
    cegos = sum(1 for _, _, _, saldo in contas if saldo is None)
    aberto = sum(saldo for _, _, _, saldo in contas if saldo is not None)
    folgas = sum(folga_do_termo(bruto, perdoadas)
                 for _, bruto, perdoadas, _ in contas)
    if cegos:
        print(VOCABULARIO_NAO_MEDIDO.format(cegos))
    elif aberto:
        print(VOCABULARIO_ABERTO.format(aberto))
    elif folgas:
        print(VOCABULARIO_COM_FOLGA.format(folgas))
    else:
        print(VOCABULARIO_FECHADO)
    return 1 if (aberto or cegos or folgas) else 0


def entrega(raiz: Path) -> int:
    codigo, atual = corre(f'cd "{raiz}" && {COMANDO_DA_BRANCH}')
    if codigo != 0 or not atual:
        print(FORA_DE_REPOSITORIO)
        return 0
    print(f"\n{TITULO_ENTREGA}")
    codigo, alvo = corre(f'cd "{raiz}" && {COMANDO_DO_UPSTREAM}')
    if codigo != 0 or not alvo:
        codigo, alvo = corre(
            f'cd "{raiz}" && {COMANDO_DO_ESPELHO.format(atual)}')
    if codigo != 0 or not alvo:
        print(SEM_ENTREGA.format(atual, atual))
        return 1
    _, sobra = corre(
        f'cd "{raiz}" && {COMANDO_DO_QUE_FALTA.format(alvo)}')
    linhas = [l for l in sobra.split("\n") if l.strip()]
    if not linhas:
        print(ENTREGA_LIMPA.format(atual, alvo))
        return 0
    print(ENTREGA_COM_SOBRA.format(len(linhas), atual, alvo))
    for linha in linhas:
        print(f"  {linha}")
    return 1


def teto_da_largada(raiz: Path):
    try:
        dado = json.loads(
            (raiz / ARQUIVO_DE_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    declarado = dado.get(CHAVE_DO_TETO) if isinstance(dado, dict) else None
    return declarado if isinstance(declarado, int) else None


def largada(raiz: Path) -> int:
    print(f"\n{TITULO_LARGADA}")
    paga = medir(raiz)[1]["largada"]
    teto = teto_da_largada(raiz)
    if teto is None:
        print(LARGADA_SEM_TETO.format(paga, ARQUIVO_DE_CONFIGURACAO,
                                      CHAVE_DO_TETO))
        return 0
    if paga > teto:
        print(LARGADA_ACIMA.format(paga, teto))
        return 1
    print(LARGADA_NA_REGUA.format(paga, teto))
    return 0


def subagentes(raiz: Path) -> tuple:
    achados = sorted((raiz / PASTA_DOS_SUBAGENTES).glob(GLOB_PAGINA))
    sem_coleira = [a.name for a in achados
                   if not CAMPO_DAS_FERRAMENTAS.search(
                       a.read_text(encoding="utf-8", errors="replace"))]
    return achados, sem_coleira


def medir(raiz: Path) -> tuple:
    instrucoes = sum(len((raiz / n).read_bytes())
                     for n in CARREGADOS_EM_TODA_SESSAO if (raiz / n).is_file())
    catalogo = adiado = 0
    skills = sorted(pasta_das_skills(raiz).glob(GLOB_SKILL))
    for skill in skills:
        listada, corpo = catalogo_e_corpo(skill)
        catalogo += len(listada.encode())
        adiado += corpo
    paginas = sorted((raiz / PASTA_DO_CONHECIMENTO).glob(GLOB_PAGINA))
    achados_de_subagente, subagentes_sem_coleira = subagentes(raiz)
    contas_do_vocabulario = saldo_do_vocabulario(raiz)
    injetado_por_gancho, ganchos_cegos = bytes_que_os_ganchos_injetam(
        raiz)
    dados = {
        "largada": instrucoes + catalogo + injetado_por_gancho,
        "instrucoes": instrucoes,
        "catalogo": catalogo,
        "injetado_por_gancho": injetado_por_gancho,
        "ganchos_nao_medidos": ganchos_cegos,
        "adiado": adiado,
        "skills": len(skills),
        "paginas": len(paginas),
        "bytes_das_paginas": sum(len(p.read_bytes()) for p in paginas),
        "ganchos": len(sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))),
        "subagentes": len(achados_de_subagente),
        "vocabulario_aberto": sum(
            saldo for _, _, _, saldo in contas_do_vocabulario
            if saldo is not None),
        "vocabulario_nao_medido": sum(
            1 for _, _, _, saldo in contas_do_vocabulario
            if saldo is None),
        "subagentes_sem_coleira": len(subagentes_sem_coleira),
        "regras": quantas_regras(raiz),
    }
    linhas = [
        LINHA.format("largada — o que TODA sessão paga",
                     f"{dados['largada']} bytes"),
        LINHA.format("  instruções (AGENTS.md, CLAUDE.md)",
                     f"{dados['instrucoes']} bytes"),
        LINHA.format(f"  catálogo de {dados['skills']} skills",
                     f"{dados['catalogo']} bytes"),
        LINHA.format("  injetado por gancho de abertura",
                     f"{dados['injetado_por_gancho']} bytes"
                     + (f" ({dados['ganchos_nao_medidos']} gancho(s) não medido(s))"
                        if dados["ganchos_nao_medidos"] else "")),
        LINHA.format("corpo de skill — só ao disparar",
                     f"{dados['adiado']} bytes"),
        LINHA.format(f"páginas em {PASTA_DO_CONHECIMENTO}/",
                     f"{dados['paginas']} ({dados['bytes_das_paginas']} bytes)"),
        LINHA.format("ganchos no disco", dados["ganchos"]),
        LINHA.format("subagentes no disco",
                     f"{dados['subagentes']}"
                     f" ({dados['subagentes_sem_coleira']} sem coleira)"),
    ]
    return linhas, dados


def resumo_da_suite(saida: str) -> str:
    linhas = [l for l in saida.splitlines() if l.strip()]
    resumo = next((l for l in reversed(linhas)
                   if l.startswith(MARCAS_DE_RESUMO)), linhas[-1] if linhas else "")
    return resumo[:52]


def instrumentos_com_teste(raiz: Path) -> list:
    alvos = sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
    alvos += sorted((raiz / PASTA_DOS_INSTRUMENTOS).glob(f"*/{GLOB_PYTHON}"))
    if (raiz / INSTALADOR).is_file():
        alvos.append(raiz / INSTALADOR)
    return [a for a in alvos
            if BANDEIRA_DE_TESTE in a.read_text(encoding="utf-8", errors="replace")]


def provar(raiz: Path) -> tuple:
    linhas, caidos, rodados = [], [], 0
    for alvo in instrumentos_com_teste(raiz):
        codigo, saida = corre(
            f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} "{alvo.relative_to(raiz)}" {BANDEIRA_DE_TESTE}')
        rodados += 1
        passou = codigo == 0
        if not passou:
            caidos.append(alvo.name)
        linhas.append(LINHA_DE_CASO.format(
            "OK  " if passou else "CAIU",
            f"{alvo.relative_to(raiz)} — {resumo_da_suite(saida)}"))
    sem_teste = [p.name for p in sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
                 if BANDEIRA_DE_TESTE not in p.read_text(encoding="utf-8",
                                                         errors="replace")]
    for nome in sem_teste:
        linhas.append(LINHA_DE_CASO.format("CAIU", f"{nome} — sem --testar próprio"))
    if (raiz / INSTALADOR).is_file():
        codigo, _ = corre(f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} {INSTALADOR} --verificar')
        rodados += 1
        if codigo != 0:
            caidos.append(INSTALADOR)
        linhas.append(LINHA_DE_CASO.format(
            "OK  " if codigo == 0 else "CAIU", f"{INSTALADOR} --verificar"))
    return linhas, {"rodados": rodados, "caem": len(caidos) + len(sem_teste),
                    "sem_teste": len(sem_teste)}


def _texto(valor):
    return str(valor).lower()


def _comeca_com(valor, aceitos):
    return _texto(valor).lstrip(' "\'').startswith(tuple(aceitos))


def quantas_regras(raiz: Path) -> int:
    fonte = raiz / FONTE_DAS_REGRAS
    if not fonte.is_file():
        return 0
    try:
        return len(json.loads(fonte.read_text(encoding="utf-8"))["regras"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return 0


def perguntas(quantas_regras):
    return (
        ("abre na raiz", "onde_abrir",
         lambda r: "raiz" in _texto(r.get("onde_abrir"))),
        ("conta as regras", "quantas_regras",
         lambda r: r.get("quantas_regras") == quantas_regras),
        ("não commita por conta", "posso_commitar",
         lambda r: _comeca_com(r.get("posso_commitar"),
                               ("nao", "não", "depende"))),
        ("segredo vira variável", "segredo_em_texto_rastreado",
         lambda r: "${" in str(r.get("segredo_em_texto_rastreado"))
         or "variáve" in _texto(r.get("segredo_em_texto_rastreado"))
         or "variave" in _texto(r.get("segredo_em_texto_rastreado"))),
        ("não toca em branch de longa duração", "branch_de_longa_duracao",
         lambda r: any(p in _texto(r.get("branch_de_longa_duracao"))
                       for p in ("não", "nao", "nunca"))),
        ("pronto é o que instrumento provou", "o_que_e_pronto",
         lambda r: "instrumento" in _texto(r.get("o_que_e_pronto"))
         or "prov" in _texto(r.get("o_que_e_pronto"))),
    )


def colher_json(texto: str) -> dict:
    for corte in (texto, texto[texto.find("{"):texto.rfind("}") + 1]):
        with contextlib.suppress(ValueError):
            dado = json.loads(corte)
            if isinstance(dado, dict):
                return dado
    return {}


def teste_toca_o_proprio_codigo(caminho: Path) -> bool:
    with contextlib.suppress(OSError, SyntaxError):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        do_arquivo = {no.name for no in ast.walk(arvore)
                      if isinstance(no, FORMAS_DE_FUNCAO)}
        for no in ast.walk(arvore):
            if not isinstance(no, FORMAS_DE_FUNCAO):
                continue
            if MARCA_DE_TESTE_NO_NOME not in no.name:
                continue
            chamados = {c.func.id for c in ast.walk(no)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            if chamados & (do_arquivo - {no.name}):
                return True
    return False


def simular(raiz: Path) -> tuple:
    if not shutil.which("claude"):
        return [SEM_CLAUDE], {"rodou": False}
    fonte = raiz / FONTE_DAS_REGRAS
    if not fonte.is_file():
        return [SEM_REGRAS], {"rodou": False}

    quantas = len(json.loads(fonte.read_text(encoding="utf-8"))["regras"])
    alvo = raiz / ARQUIVO_PEDIDO
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        alvo.unlink()

    partida = time.monotonic()
    _, bruto = corre(
        f'cd "{raiz}" && claude -p {json.dumps(PEDIDO.format(arquivo=ARQUIVO_PEDIDO))} '
        f'--output-format json --model {MODELO_DA_SIMULACAO} '
        f'--allowedTools "{FERRAMENTAS_DA_SIMULACAO}"',
        tempo=TEMPO_DA_SIMULACAO)
    parede = time.monotonic() - partida

    sessao = colher_json(bruto)
    resposta = colher_json(str(sessao.get("result", "")))
    do_nucleo = [(rotulo, bool(prova(resposta)),
                  "" if prova(resposta) else str(resposta.get(chave, ""))[:44])
                 for rotulo, chave, prova in perguntas(quantas)]
    do_artefato = []

    if alvo.is_file():
        codigo_do_teste, berro = corre(
            f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} "{ARQUIVO_PEDIDO}" {BANDEIRA_DE_TESTE}')
    else:
        codigo_do_teste, berro = 1, "a sessão não escreveu o arquivo"
    do_artefato.append((f"entregou {ARQUIVO_PEDIDO} com --testar que passa",
                        alvo.is_file() and codigo_do_teste == 0,
                        berro.strip().splitlines()[-1][:44] if berro else ""))
    do_artefato.append(("o --testar exercita o código do arquivo",
                        alvo.is_file() and teste_toca_o_proprio_codigo(alvo),
                        ""))
    acertos = do_nucleo + do_artefato
    with contextlib.suppress(OSError):
        alvo.unlink()

    certos = sum(1 for _, ok, _ in acertos if ok)
    uso = sessao.get("usage") or {}
    linhas = [LINHA_DE_CASO.format("OK  " if ok else "CAIU",
                                   f"{rotulo}{'  ' + porque if porque else ''}")
              for rotulo, ok, porque in acertos]
    linhas += [
        LINHA.format("acurácia", f"{certos}/{len(acertos)}"),
        LINHA.format("turnos", sessao.get("num_turns", "?")),
        LINHA.format("tempo de parede", f"{parede:.1f} s"),
        LINHA.format("dólar", f"{sessao.get('total_cost_usd', 0):.4f}"),
        LINHA.format("tokens de saída", uso.get("output_tokens", "?")),
    ]
    return linhas, {"rodou": True, "acertos": certos, "casos": len(acertos),
                    "certas_do_nucleo": sum(1 for _, ok, _ in do_nucleo if ok),
                    "casos_do_nucleo": len(do_nucleo),
                    "caidas_do_nucleo": [rotulo for rotulo, ok, _
                                         in do_nucleo if not ok],
                    "caidas_do_artefato": [rotulo for rotulo, ok, _
                                           in do_artefato if not ok],
                    "turnos": sessao.get("num_turns"),
                    "segundos": round(parede, 1),
                    "dolar": sessao.get("total_cost_usd")}


PASSOS = (
    ("medir", TITULO_MEDIR, medir),
    ("provar", TITULO_PROVAR, provar),
    ("simular", TITULO_SIMULAR, simular),
)

NUMEROS = {
    "largada": ("medir", "largada"),
    "adiado": ("medir", "adiado"),
    "paginas": ("medir", "paginas"),
    "ganchos": ("medir", "ganchos"),
    "subagentes": ("medir", "subagentes"),
    "vocabulario-aberto": ("medir", "vocabulario_aberto"),
    "vocabulario-nao-medido": ("medir", "vocabulario_nao_medido"),
    "subagentes-sem-coleira": ("medir", "subagentes_sem_coleira"),
    "injetado-por-gancho": ("medir", "injetado_por_gancho"),
    "ganchos-nao-medidos": ("medir", "ganchos_nao_medidos"),
    "instrumentos-que-caem": ("provar", "caem"),
    "ganchos-sem-teste": ("provar", "sem_teste"),
    "acertos-da-simulacao": ("simular", "acertos"),
    "regras-da-camada": ("medir", "regras"),
}


PROVAS = {
    "medir": (("a largada que toda sessão paga, em bytes", "largada"),
              ("o corpo de skill adiado, em bytes", "adiado"),
              ("páginas de conhecimento", "paginas")),
    "provar": (("instrumentos que caem", "instrumentos-que-caem"),),
    "simular": (("as regras que o gabarito da simulação cobra",
                 "regras-da-camada"),),
}
SUPOSTO_DA_SIMULACAO = (
    "a sessão acertou {acertos} de {casos} checagens, em {turnos} turnos, "
    "{segundos}s e US$ {dolar}. Este número NÃO entra em provado: é uma "
    "sessão de verdade, e re-executar dá outro resultado.")
SUPOSTO_SEM_SIMULACAO = ("a simulação não rodou: falta o claude no PATH ou o "
                         "nucleo/regras.json.")
SUPOSTO_DO_ARTEFATO = (
    "checagem do artefato que a sessão errou, e que NÃO derruba a etapa "
    "porque oscila entre execuções: {}.")
VEREDITO_SEGUE = "segue"
VEREDITO_PARA = "para"
COMANDO_DO_NUMERO = "{} .agents/camada/camada.py --numero {}"
FALTA_DO_PASSO = "{}: {}"
PROXIMO_DO_PASSO = ("Leia a evidência, conserte o que o número acusa e "
                    "reexecute esta etapa.")


def julgar_a_simulacao(resumo: dict) -> tuple:
    if not resumo.get("rodou"):
        return [], [SUPOSTO_SEM_SIMULACAO]
    suposto = [SUPOSTO_DA_SIMULACAO.format(
        acertos=resumo["acertos"], casos=resumo["casos"],
        turnos=resumo["turnos"], segundos=resumo["segundos"],
        dolar=f"{resumo['dolar'] or 0:.4f}")]
    faltas = []
    if resumo["certas_do_nucleo"] < resumo["casos_do_nucleo"]:
        faltas.append(FALTA_DO_PASSO.format(
            "checagens determinísticas que a sessão errou",
            ", ".join(resumo.get("caidas_do_nucleo") or [])
            or resumo["casos_do_nucleo"] - resumo["certas_do_nucleo"]))
    if resumo["caidas_do_artefato"]:
        suposto.append(SUPOSTO_DO_ARTEFATO.format(
            ", ".join(resumo["caidas_do_artefato"])))
    return faltas, suposto


def evidencia(raiz: Path, passo: str) -> dict:
    resumo = rodar_passos(raiz, {passo}, calado=True)[passo]
    provado, faltas = [], []
    for afirmacao, chave in PROVAS[passo]:
        comando = COMANDO_DO_NUMERO.format(
            interpretador_com_nome_portatil(), chave)
        codigo, saida = corre(f'cd "{raiz}" && {comando}')
        provado.append({"afirmacao": afirmacao, "comando": comando,
                        "saida": saida})
        if codigo != 0:
            faltas.append(FALTA_DO_PASSO.format(chave, saida[:120]))
    if passo == "provar" and resumo.get("caem"):
        faltas.append(FALTA_DO_PASSO.format(
            "instrumentos que caem", resumo["caem"]))
    suposto = []
    if passo == "simular":
        do_simular, suposto = julgar_a_simulacao(resumo)
        faltas += do_simular
    dado = {"veredito": VEREDITO_PARA if faltas else VEREDITO_SEGUE,
            "provado": provado, "suposto": suposto, "faltas": faltas}
    if faltas:
        dado["proximo"] = PROXIMO_DO_PASSO
    return dado


def rodar_passos(raiz: Path, escolhidos: set, calado: bool) -> dict:
    resumo = {}
    for nome, titulo, passo in PASSOS:
        if escolhidos and nome not in escolhidos:
            continue
        linhas, dados = passo(raiz)
        if not calado:
            print(f"\n{titulo}")
            for linha in linhas:
                print(linha)
        resumo[nome] = dados
    return resumo


def um_numero(raiz: Path, chave: str) -> int:
    if chave not in NUMEROS:
        sys.exit(NUMERO_DESCONHECIDO.format(chave, " ".join(sorted(NUMEROS))))
    passo, campo = NUMEROS[chave]
    resumo = rodar_passos(raiz, {passo}, calado=True)
    print(resumo[passo].get(campo, ""))
    return 0


def testar() -> int:
    falhas = []

    def caso(rotulo, passou):
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        (raiz / "AGENTS.md").write_text("abc\n", encoding="utf-8")
        (raiz / PASTA_DO_CONHECIMENTO).mkdir()
        (raiz / PASTA_DOS_GANCHOS).mkdir(parents=True)
        skill = raiz / PASTA_DAS_SKILLS_FONTE / "s"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: s\ndescription: faz algo\n---\n\ncorpo longo aqui\n",
            encoding="utf-8")

        _, dados = medir(raiz)
        caso("a largada soma instruções mais catálogo, nunca o corpo",
             dados["largada"] == 4 + len("- s: faz algo\n".encode()))

        injecao = "regra que o gancho injeta\n"
        (raiz / "gancho.py").write_text(
            "import json\n"
            "print(json.dumps({'hookSpecificOutput': "
            "{'additionalContext': %r}}))\n" % injecao,
            encoding="utf-8")
        (raiz / ".claude").mkdir(exist_ok=True)
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command", "command":
                 f'{INTERPRETADOR_NO_SHELL} "${{CLAUDE_PROJECT_DIR}}/gancho.py"'}]}]}}),
            encoding="utf-8")
        _, com_gancho = medir(raiz)
        caso("o gancho de abertura entra na conta",
             com_gancho["injetado_por_gancho"] == len(injecao.encode()))
        caso("e a largada cresce exatamente o que ele injeta",
             com_gancho["largada"]
             == dados["largada"] + len(injecao.encode()))
        (raiz / "gancho.py").write_text(
            "print('nao sou json')\n", encoding="utf-8")
        caso("gancho que RODA e não injeta vale zero, não cego",
             medir(raiz)[1]["injetado_por_gancho"] == 0
             and medir(raiz)[1]["ganchos_nao_medidos"] == 0)
        (raiz / "gancho.py").write_text("import sys\nsys.exit(1)\n",
                                        encoding="utf-8")
        caso("gancho que CAI não derruba a medida, e conta como cego",
             medir(raiz)[1]["injetado_por_gancho"] == 0
             and medir(raiz)[1]["ganchos_nao_medidos"] == 1)
        (raiz / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"SessionStart": [{"hooks": [
                {"type": "command",
                 "command": "binario-que-nao-existe-nenhum"}]}]}}),
            encoding="utf-8")
        caso("gancho que NÃO RODOU é contado como não medido",
             medir(raiz)[1]["ganchos_nao_medidos"] == 1)
        caso("o corpo da skill fica no adiado", dados["adiado"] > 0)
        caso("conta as skills", dados["skills"] == 1)

        listada, corpo = catalogo_e_corpo(skill / "SKILL.md")
        caso("o catálogo é nome e descrição", listada == "- s: faz algo\n")
        caso("o corpo é o que sobra do frontmatter", corpo > 0)

        sem_frente = raiz / "solta.md"
        sem_frente.write_text("só corpo\n", encoding="utf-8")
        caso("skill sem frontmatter não vira catálogo",
             catalogo_e_corpo(sem_frente)[0] == "")

        gancho = raiz / PASTA_DOS_GANCHOS / "g.py"
        gancho.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho sem --testar é acusado", prova["sem_teste"] == 1)
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n    sys.exit(0)\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho com --testar que passa não é acusado", prova["caem"] == 0)
        gancho.write_text(
            "import sys\nif '--testar' in sys.argv:\n    sys.exit(1)\n",
            encoding="utf-8")
        _, prova = provar(raiz)
        caso("gancho com --testar que cai é acusado", prova["caem"] == 1)

        pasta_de_subagentes = raiz / PASTA_DOS_SUBAGENTES
        pasta_de_subagentes.mkdir(parents=True, exist_ok=True)
        caso("sem subagente nenhum, conta zero e não acusa coleira",
             subagentes(raiz) == ([], []))
        (pasta_de_subagentes / "com-coleira.md").write_text(
            "---\nname: a\ndescription: faz\ntools: Read, Grep\n---\n",
            encoding="utf-8")
        (pasta_de_subagentes / "sem-coleira.md").write_text(
            "---\nname: b\ndescription: faz\n---\n", encoding="utf-8")
        achados, soltos = subagentes(raiz)
        caso("conta os subagentes do disco", len(achados) == 2)
        caso("acusa só o que herda tudo, e diz qual",
             soltos == ["sem-coleira.md"])
        _, com_subagentes = medir(raiz)
        caso("a medida carrega os dois números",
             com_subagentes["subagentes"] == 2
             and com_subagentes["subagentes_sem_coleira"] == 1)
        falso = raiz / "bin-de-mentira"
        falso.mkdir(exist_ok=True)
        alias = falso / "python3"
        alias.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
        alias.chmod(0o755)
        antes_do_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{falso}:{antes_do_path}"
        interpretador_com_nome_portatil.cache_clear()
        escolhido = interpretador_com_nome_portatil()
        os.environ["PATH"] = antes_do_path
        interpretador_com_nome_portatil.cache_clear()
        caso("python3 que existe e NAO roda é descartado — é o atalho "
             "da loja do Windows, e foi assim que a camada caiu lá",
             escolhido != "python3")
        caso("e o escolhido no lugar dele roda mesmo",
             corre(f"{escolhido} -c \"{PERGUNTA_DA_VERSAO}\"")[1].strip()
             == VERSAO_QUE_SERVE)
        nome = interpretador_com_nome_portatil()
        caso("o interpretador portátil é um nome, não um caminho",
             nome in CANDIDATOS_DE_INTERPRETADOR)
        caso("e o nome escolhido roda mesmo um Python 3",
             corre(f"{nome} -c \"{PERGUNTA_DA_VERSAO}\"")[1].strip()
             == VERSAO_QUE_SERVE)
        caso("o que executa por dentro é o intérprete desta sessão",
             INTERPRETADOR == sys.executable
             and INTERPRETADOR_NO_SHELL.strip('"') == sys.executable)
        caso("sem teto declarado, mede e não cobra",
             teto_da_largada(raiz) is None and largada(raiz) == 0)
        (raiz / "nucleo").mkdir(exist_ok=True)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": 1}), encoding="utf-8")
        caso("teto apertado reprova, e diz o número",
             teto_da_largada(raiz) == 1 and largada(raiz) == 1)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": 10 ** 9}),
            encoding="utf-8")
        caso("teto folgado passa", largada(raiz) == 0)
        (raiz / "nucleo" / "configuracao.json").write_text(
            json.dumps({"teto_da_largada_em_bytes": "muito"}),
            encoding="utf-8")
        caso("teto que não é número não vira cobrança",
             teto_da_largada(raiz) is None)
        caso("sem vocabulario.json não há o que medir",
             saldo_do_vocabulario(raiz) == [])
        (raiz / "nucleo").mkdir(exist_ok=True)
        (raiz / "nucleo" / "vocabulario.json").write_text(json.dumps(
            {"termos": [
                {"id": "aberto", "excecoes": [],
                 "pronto": {"padrao": r"(?i)\bfoo\b"}},
                {"id": "perdoado", "excecoes": [{"ocorrencias": 2}],
                 "pronto": {"padrao": r"(?i)\bbar\b"}}]}),
            encoding="utf-8")
        (raiz / "texto.md").write_text("foo\nbar\nBar\n",
                                       encoding="utf-8")
        corre(f'cd "{raiz}" && git init -q && git add -A')
        contas = dict((c[0], c[1:]) for c in saldo_do_vocabulario(raiz))
        caso("termo sem exceção acusa o saldo cheio",
             contas["aberto"] == (1, 0, 1))
        caso("exceção declarada desconta, e o padrão pega maiúscula",
             contas["perdoado"] == (2, 2, 0))
        caso("a medida carrega o saldo aberto",
             medir(raiz)[1]["vocabulario_aberto"] == 1)
        caso("o flag sai 1 quando algum termo reabriu",
             vocabulario(raiz) == 1)

        caso("o lote respeita o teto e não perde caminho",
             [c for lote in lotes_de_caminhos(["a" * 40] * 50)
              for c in lote] == ["a" * 40] * 50)
        caso("lista curta cabe num lote só",
             len(lotes_de_caminhos(["curto"])) == 1)
        caso("grep que ERRA devolve não medido, nunca zero",
             quantas_linhas_casam("(", ["texto.md"], raiz) is None)
        caso("grep que não acha devolve zero de verdade",
             quantas_linhas_casam("(?i)zzzz", ["texto.md"], raiz) == 0)
        (raiz / "nucleo" / "vocabulario.json").write_text(json.dumps(
            {"termos": [{"id": "quebrado", "excecoes": [],
                         "pronto": {"padrao": "("}}]}), encoding="utf-8")
        caso("termo com padrão quebrado não vira fechado",
             saldo_do_vocabulario(raiz)[0][3] is None)
        caso("e o flag sai 1 em vez de dizer verde",
             vocabulario(raiz) == 1)
        caso("a medida conta o que não foi medido",
             medir(raiz)[1]["vocabulario_nao_medido"] == 1)
        caso("exceção que sobra é folga, e folga esconde termo reabrindo",
             folga_do_termo(10, 11) == 1)
        caso("exceção que bate com o disco não é folga",
             folga_do_termo(10, 10) == 0)
        caso("exceção menor que o medido é saldo, não folga",
             folga_do_termo(11, 10) == 0)
        caso("termo não medido não vira folga inventada",
             folga_do_termo(None, 7) == 0)


        bom = raiz / "bom.py"
        bom.write_text("def somar(n):\n    return sum(n)\n"
                       "def testar():\n    assert somar([1]) == 1\n",
                       encoding="utf-8")
        ruim = raiz / "ruim.py"
        ruim.write_text("def testar():\n    assert sum([1]) == 1\n",
                        encoding="utf-8")
        caso("teste que chama função do arquivo conta",
             teste_toca_o_proprio_codigo(bom))
        caso("teste que só usa embutido não conta",
             not teste_toca_o_proprio_codigo(ruim))
        assincrono = raiz / "assincrono.py"
        assincrono.write_text(
            "async def buscar(n):\n    return n\n"
            "async def testar():\n    assert await buscar(1) == 1\n",
            encoding="utf-8")
        caso("teste assíncrono que chama função do arquivo conta",
             teste_toca_o_proprio_codigo(assincrono))
        mista = raiz / "mista.py"
        mista.write_text(
            "async def buscar(n):\n    return n\n"
            "def testar():\n    assert buscar(1)\n",
            encoding="utf-8")
        caso("teste comum que chama função assíncrona do arquivo conta",
             teste_toca_o_proprio_codigo(mista))

    caso("o JSON sai de dentro de cerca de código",
         colher_json('```json\n{"a": 1}\n```') == {"a": 1})
    caso("texto sem JSON devolve vazio", colher_json("nada aqui") == {})
    gabarito = {p[1]: p[2] for p in perguntas(14)}
    caso("commitar: 'não' passa", gabarito["posso_commitar"](
        {"posso_commitar": "não — sem autorização declarada"}))
    caso("commitar: 'sim' não passa", not gabarito["posso_commitar"](
        {"posso_commitar": "sim, pode"}))
    caso("as regras se contam pelo número da fonte",
         gabarito["quantas_regras"]({"quantas_regras": 14})
         and not gabarito["quantas_regras"]({"quantas_regras": 13}))
    caso("a acurácia não entra em provado: ela varia sozinha",
         all(chave != "acertos-da-simulacao"
             for _, chave in PROVAS["simular"]))
    caso("mas a simulação prova algo determinístico, senão segue sem prova",
         PROVAS["simular"] != ()
         and all(NUMEROS[chave][0] != "simular"
                 for _, chave in PROVAS["simular"]))

    def resumo_de(certas, caidas):
        return {"rodou": True, "acertos": certas + 2 - len(caidas), "casos": 8,
                "certas_do_nucleo": certas, "casos_do_nucleo": 6,
                "caidas_do_nucleo": ["abre na raiz"] * (6 - certas),
                "caidas_do_artefato": caidas, "turnos": 5, "segundos": 40.0,
                "dolar": 0.07}

    caso("as 6 determinísticas certas seguem, mesmo com o artefato caído",
         julgar_a_simulacao(resumo_de(6, ["o --testar exercita o código"]))[0]
         == [])
    caso("a checagem do artefato que cai vira suposto, com o nome",
         any("o --testar exercita o código" in dito
             for dito in julgar_a_simulacao(
                 resumo_de(6, ["o --testar exercita o código"]))[1]))
    caso("determinística errada derruba a etapa, e a falta diz qual",
         julgar_a_simulacao(resumo_de(5, []))[0]
         and "abre na raiz" in julgar_a_simulacao(resumo_de(5, []))[0][0])
    caso("tudo certo não gera falta nem suposto de artefato",
         julgar_a_simulacao(resumo_de(6, []))[0] == []
         and len(julgar_a_simulacao(resumo_de(6, []))[1]) == 1)
    caso("simulação que não rodou não inventa falta",
         julgar_a_simulacao({"rodou": False}) == ([], [SUPOSTO_SEM_SIMULACAO]))
    caso("toda prova declarada tem número que a imprime",
         all(chave in NUMEROS for provas in PROVAS.values()
             for _, chave in provas))

    with tempfile.TemporaryDirectory(prefix="camada-entrega-") as sozinho:
        repositorio = Path(sozinho) / "repositorio"
        repositorio.mkdir()
        assinatura = ("-c user.name=t -c user.email=t@t "
                      "-c commit.gpgsign=false")
        corre(f'cd "{repositorio}" && git init -q && echo a > a.txt && git add -A && git {assinatura} commit -qm um')
        caso("sem remoto nenhum, a entrega não se prova",
             entrega(repositorio) == 1)
        remoto = Path(sozinho) / "remoto.git"
        corre(f'git init -q --bare "{remoto}"')
        corre(f'cd "{repositorio}" && git remote add origin "{remoto}" && git push -q origin HEAD:refs/heads/$(git branch --show-current)')
        caso("tudo empurrado, a entrega está limpa",
             entrega(repositorio) == 0)
        corre(f'cd "{repositorio}" && echo b > b.txt && git add -A && git {assinatura} commit -qm dois')
        caso("commit que não saiu da máquina reprova",
             entrega(repositorio) == 1)

    total = 65
    if falhas:
        print(f"FALHOU: {len(falhas)} de {total} casos")
        for falha in falhas:
            print(f"  [{falha}]")
        return 1
    print(f"OK: {total} casos — medida, prova e gabarito da simulação")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("passo", nargs="*", choices=[p[0] for p in PASSOS] or None,
                    help="quais passos rodar (padrão: medir e provar)")
    ap.add_argument("--evidencia", choices=[p[0] for p in PASSOS],
                    help="emite a evidência de um passo, para o executor de roteiros")
    ap.add_argument("--numero", help="imprime um número só, para virar prova")
    ap.add_argument("--largada", action="store_true",
                    help="cobra o teto de bytes que toda sessão paga")
    ap.add_argument("--entrega", action="store_true",
                    help="prova que nada ficou fora da branch de entrega")
    ap.add_argument("--vocabulario", action="store_true",
                    help="mede o fechamento dos termos e sai 1 se algum reabriu")
    ap.add_argument("--resumo", action="store_true",
                    help="só o JSON, para comparar entre rodadas")
    ap.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                    dest="testar", help="roda os casos deste instrumento")
    a = ap.parse_args()

    if a.testar:
        return testar()

    raiz = Path.cwd()
    if not (raiz / PASTA_DO_CONHECIMENTO).is_dir():
        sys.exit(FORA_DA_RAIZ.format(PASTA_DO_CONHECIMENTO))

    if a.largada:
        return largada(raiz)

    if a.entrega:
        return entrega(raiz)

    if a.vocabulario:
        return vocabulario(raiz)

    if a.numero:
        return um_numero(raiz, a.numero)

    if a.evidencia:
        print(json.dumps(evidencia(raiz, a.evidencia),
                         ensure_ascii=False))
        return 0

    escolhidos = set(a.passo) or {"medir", "provar"}
    resumo = rodar_passos(raiz, escolhidos, calado=a.resumo)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
