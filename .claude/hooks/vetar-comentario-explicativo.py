import ast
import json
import os
import sys
import tempfile
from pathlib import Path

MARCAS_POR_EXTENSAO = {
    ".cs": ("//", "/*"),
    ".ts": ("//", "/*"),
    ".js": ("//", "/*"),
    ".vue": ("//", "/*", "<!--"),
    ".py": ("#",),
    ".sh": ("#",),
}
SHEBANG = "#!"
ARQUIVO_DAS_DIRETIVAS = ".claude/diretivas-de-ferramenta.txt"
MARCA_DE_COMENTARIO = "#"
SEM_DIRETIVAS = ()

EXTENSAO_DO_PYTHON = ".py"
ASPAS = ('"', "'")
ASPAS_TRIPLAS = ('"""', "'''")
MARCA_DE_REPOSITORIO_VIZINHO = ".git"
ABERTURAS_DE_CORPO = ("def ", "async def ", "class ")
FIM_DE_ABERTURA = ":"
FIM_DE_ASSINATURA_QUEBRADA = "):"
NOS_QUE_LEVAM_DOCSTRING = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)

FERRAMENTA_DE_ESCRITA_INTEIRA = "Write"
FERRAMENTA_DE_UMA_EDICAO = "Edit"
FERRAMENTA_DE_VARIAS_EDICOES = "MultiEdit"
CAMPO_DO_CAMINHO = "file_path"
CAMPO_DO_CONTEUDO = "content"
CAMPO_DO_TEXTO_VELHO = "old_string"
CAMPO_DO_TEXTO_NOVO = "new_string"
CAMPO_DAS_EDICOES = "edits"

MARCA_DE_REPOSITORIO = ".git"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
DECISAO_DE_PERGUNTAR = "ask"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO = "bypassPermissions"
MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
BANDEIRA_DE_TESTE = "--testar"
PASSA = ""
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

RECUSA = (
    "Regra 14 da camada: esta escrita acrescenta uma linha de comentário "
    "em {}:\n"
    "    {}\n"
    "Comentário explicativo é sinal de nome errado: o nome tem de dizer o "
    "que o comentário diria. Renomeie a função, a variável ou o arquivo até "
    "a linha se explicar sozinha, ou extraia o trecho para uma função com "
    "nome que conte a história. O POR QUÊ de uma decisão não mora no "
    "código: mora na issue, na mensagem do commit ou em `conhecimento/`, "
    "onde quem decide procura. Arquivo de teste não é exceção.\n"
    "Passam só as exceções mecânicas: shebang e diretiva de ferramenta "
    "({}) — a lista é do dono e mora em {}."
)
APRENDIZADO = (
    "comentário em código é recusado: o nome diz o que o comentário "
    "diria, e o porquê vai para a issue ou para a mensagem do commit."
)
RECUSA_DE_DOCSTRING = (
    "Regra 14 da camada: esta escrita acrescenta uma docstring em {}, que "
    "mora na raiz da camada:\n"
    "    {}\n"
    "Docstring é comentário explicativo na régua desta casa: o nome tem de "
    "dizer o que ela diria. Renomeie o módulo, a classe ou a função até o "
    "nome contar a história, ou extraia o trecho para uma função com nome "
    "que a conte. O POR QUÊ de uma decisão não mora no código: mora na "
    "issue, na mensagem do commit ou em `conhecimento/`. Fora da raiz da "
    "camada, e dentro de repositório vizinho (projetos/<nome>), docstring é "
    "normal e passa."
)
APRENDIZADO_DA_DOCSTRING = (
    "docstring em código da camada é recusada como comentário: o nome diz o "
    "que ela diria, e o porquê vai para a issue ou para a mensagem do commit."
)
SEM_A_LISTA = (
    "nenhuma — {} não foi lida, e cerca sem a lista dela nega tudo em vez "
    "de liberar em silêncio"
)
RECUSA_DE_AFROUXAR = (
    "Regra 9 da camada: isto quer escrever em {}, que é a lista de "
    "exceções desta cerca. A lista é do dono, nunca do agente que a cerca "
    "acabou de barrar — cerca que quem foi barrado afrouxa não é cerca. O "
    "caminho: cumpra a recusa renomeando o que o comentário explicaria, "
    "ou peça ao dono a diretiva que falta. Ler o arquivo continua livre."
)
APRENDIZADO_DE_AFROUXAR = (
    "a lista de diretivas de ferramenta em {} é do dono: pedir a ele, "
    "nunca editar."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def marcas_de_comentario(caminho: str) -> tuple:
    return MARCAS_POR_EXTENSAO.get(Path(caminho).suffix.lower(), ())


def diretivas_declaradas(raiz: Path) -> tuple:
    try:
        linhas = (raiz / ARQUIVO_DAS_DIRETIVAS).read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return SEM_DIRETIVAS
    return tuple(
        l.strip().lower() for l in linhas
        if l.strip() and not l.strip().startswith(MARCA_DE_COMENTARIO))


def diretivas_para_a_mensagem(diretivas: tuple) -> str:
    if not diretivas:
        return SEM_A_LISTA.format(ARQUIVO_DAS_DIRETIVAS)
    return ", ".join(diretivas)


def escreve_na_lista_das_diretivas(caminho: str) -> bool:
    alvo = caminho.replace("\\", "/").strip().strip("\"'")
    return alvo.endswith(ARQUIVO_DAS_DIRETIVAS)


def e_excecao_mecanica(linha: str, diretivas: tuple) -> bool:
    enxuta = linha.strip()
    if enxuta.startswith(SHEBANG):
        return True
    return any(d in enxuta.lower() for d in diretivas)


def e_linha_de_comentario(linha: str, marcas: tuple) -> bool:
    enxuta = linha.strip()
    return bool(enxuta) and bool(marcas) and enxuta.startswith(marcas)


def linhas_acrescentadas(velho: str, novo: str) -> list:
    ja_estavam = {linha.strip() for linha in velho.splitlines()}
    return [linha for linha in novo.splitlines()
            if linha.strip() not in ja_estavam]


def comentario_acrescentado(caminho: str, velho: str, novo: str,
                           diretivas: tuple) -> str:
    marcas = marcas_de_comentario(caminho)
    if not marcas:
        return PASSA
    for linha in linhas_acrescentadas(velho, novo):
        if e_linha_de_comentario(linha, marcas) \
                and not e_excecao_mecanica(linha, diretivas):
            return linha.strip()
    return PASSA


def texto_no_disco(caminho: str, raiz: Path) -> str:
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = raiz / alvo
    try:
        return alvo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def pastas_entre_a_raiz_e_o_arquivo(caminho: str, raiz: Path):
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = raiz / alvo
    try:
        dentro = Path(os.path.normcase(str(alvo.resolve()))).relative_to(
            Path(os.path.normcase(str(raiz.resolve()))))
    except (ValueError, OSError):
        return None
    return dentro.parts[:-1]


def dentro_da_raiz_da_camada(caminho: str, raiz: Path) -> bool:
    partes = pastas_entre_a_raiz_e_o_arquivo(caminho, raiz)
    if partes is None:
        return False
    pasta = raiz
    for parte in partes:
        pasta = pasta / parte
        if (pasta / MARCA_DE_REPOSITORIO_VIZINHO).exists():
            return False
    return True


def tem_linha_que_comeca_com_aspas(texto: str) -> bool:
    return any(l.strip().startswith(ASPAS) for l in texto.splitlines())


def tem_aspas_triplas(texto: str) -> bool:
    return any(aspas in texto for aspas in ASPAS_TRIPLAS)


def abre_corpo(linha_enxuta: str) -> bool:
    if not linha_enxuta.endswith(FIM_DE_ABERTURA):
        return False
    return (linha_enxuta.startswith(ABERTURAS_DE_CORPO)
            or linha_enxuta.endswith(FIM_DE_ASSINATURA_QUEBRADA))


def docstring_no_fragmento(velho: str, novo: str) -> str:
    ja_estavam = {linha.strip() for linha in velho.splitlines()}
    corpo_aberto, primeira = False, True
    for linha in novo.splitlines():
        enxuta = linha.strip()
        if not enxuta:
            continue
        acrescentada = enxuta not in ja_estavam
        logo_apos_abertura = corpo_aberto and enxuta.startswith(ASPAS)
        abre_o_corpo_do_fragmento = (primeira and linha != linha.lstrip()
                                     and enxuta.startswith(ASPAS_TRIPLAS))
        if acrescentada and (logo_apos_abertura or abre_o_corpo_do_fragmento):
            return enxuta
        primeira = False
        corpo_aberto = abre_corpo(enxuta)
    return PASSA


def docstrings_de(texto: str):
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return None
    return [ast.get_docstring(no, clean=False)
            for no in ast.walk(arvore)
            if isinstance(no, NOS_QUE_LEVAM_DOCSTRING)
            and ast.get_docstring(no, clean=False) is not None]


def primeira_linha_da_docstring(dita: str) -> str:
    primeira = (dita.strip().splitlines() or [""])[0].strip()
    return ASPAS_TRIPLAS[0] + primeira + ASPAS_TRIPLAS[0]


def docstring_pela_arvore(caminho: str, velho: str, novo: str,
                          raiz: Path) -> str:
    antes = texto_no_disco(caminho, raiz)
    if velho not in antes:
        return PASSA
    novas = docstrings_de(antes.replace(velho, novo, 1))
    if novas is None:
        return PASSA
    antigas = docstrings_de(antes) or []
    for dita in novas:
        if dita not in antigas:
            return primeira_linha_da_docstring(dita)
    return PASSA


def docstring_acrescentada(caminho: str, velho: str, novo: str,
                           raiz: Path) -> str:
    if Path(caminho).suffix.lower() != EXTENSAO_DO_PYTHON:
        return PASSA
    if not tem_linha_que_comeca_com_aspas(novo):
        return PASSA
    if not dentro_da_raiz_da_camada(caminho, raiz):
        return PASSA
    no_fragmento = docstring_no_fragmento(velho, novo)
    if no_fragmento or not tem_aspas_triplas(novo):
        return no_fragmento
    return docstring_pela_arvore(caminho, velho, novo, raiz)


def escritas_com_texto_do_pedido(entrada: dict, raiz: Path) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    caminho = dado.get(CAMPO_DO_CAMINHO, "")
    if not caminho:
        return []
    if ferramenta == FERRAMENTA_DE_ESCRITA_INTEIRA:
        return [(caminho, texto_no_disco(caminho, raiz),
                 dado.get(CAMPO_DO_CONTEUDO, ""))]
    if ferramenta == FERRAMENTA_DE_VARIAS_EDICOES:
        return [(caminho, edicao.get(CAMPO_DO_TEXTO_VELHO, ""),
                 edicao.get(CAMPO_DO_TEXTO_NOVO, ""))
                for edicao in dado.get(CAMPO_DAS_EDICOES) or []
                if isinstance(edicao, dict)]
    if ferramenta == FERRAMENTA_DE_UMA_EDICAO:
        return [(caminho, dado.get(CAMPO_DO_TEXTO_VELHO, ""),
                 dado.get(CAMPO_DO_TEXTO_NOVO, ""))]
    return []


def raiz_do_alvo(caminho: str, declarada: Path) -> Path:
    alvo = Path(str(caminho).replace("\\", "/"))
    if not alvo.is_absolute():
        return declarada
    try:
        alvo.resolve().relative_to(declarada.resolve())
        return declarada
    except (ValueError, OSError):
        pass
    donas = [p for p in alvo.resolve().parents
             if (p / MARCA_DE_REPOSITORIO).exists()]
    return donas[-1] if donas else declarada


def fora_de_todo_repositorio(caminho: str, raiz: Path) -> bool:
    alvo = Path(str(caminho).replace("\\", "/"))
    if not alvo.is_absolute():
        return False
    try:
        alvo.resolve().relative_to(raiz.resolve())
        return False
    except (ValueError, OSError):
        pass
    return not any((pasta / MARCA_DE_REPOSITORIO).exists()
                   for pasta in alvo.resolve().parents)


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
    }}))
    return SILENCIO


def e_etapa_sem_ninguem(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_DE_ETAPA_NO_AMBIENTE))


def modo_que_nao_mostra_a_pergunta(entrada: dict) -> bool:
    return (entrada or {}).get(
        CAMPO_DO_MODO_DE_PERMISSAO) == MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO


def verbo_do_veto(entrada: dict, ambiente) -> str:
    if (e_etapa_sem_ninguem(ambiente)
            or modo_que_nao_mostra_a_pergunta(entrada)):
        return DECISAO_DE_NEGAR
    return DECISAO_DE_PERGUNTAR


def vetar(entrada: dict, razao: str, ambiente) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": verbo_do_veto(entrada, ambiente),
        "permissionDecisionReason": razao,
    }}))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    diretivas = diretivas_declaradas(raiz)
    for caminho, velho, novo in escritas_com_texto_do_pedido(entrada, raiz):
        if escreve_na_lista_das_diretivas(caminho):
            return vetar(entrada, RECUSA_DE_AFROUXAR.format(
                ARQUIVO_DAS_DIRETIVAS) + MANDA_GRAVAR.format(
                    APRENDIZADO_DE_AFROUXAR.format(ARQUIVO_DAS_DIRETIVAS)),
                os.environ)
        linha = comentario_acrescentado(caminho, velho, novo, diretivas)
        if linha and not fora_de_todo_repositorio(caminho, raiz):
            return vetar(entrada, RECUSA.format(
                Path(caminho).name, linha,
                diretivas_para_a_mensagem(diretivas), ARQUIVO_DAS_DIRETIVAS)
                + MANDA_GRAVAR.format(APRENDIZADO), os.environ)
        dita = docstring_acrescentada(caminho, velho, novo,
                                      raiz_do_alvo(caminho, raiz))
        if dita:
            return vetar(entrada, RECUSA_DE_DOCSTRING.format(
                Path(caminho).name, dita)
                + MANDA_GRAVAR.format(APRENDIZADO_DA_DOCSTRING), os.environ)
    return SILENCIO


BARRA = (
    ("comentário de linha em .ts", "src/laco.ts",
     "", "const total = 1\n// explica o laço"),
    ("comentário de linha em .py", "app/conta.py",
     "", "total = 1\n# soma os itens da lista"),
    ("abertura de bloco em .js", "src/conta.js",
     "", "/**\n * devolve o total\n */\nfunction f() {}"),
    ("comentário de linha em .cs", "Servico.cs",
     "", "var total = 1;\n// guarda o total antes do laço"),
    ("comentário de template em .vue", "Grade.vue",
     "", "<template>\n  <!-- a lista dos itens -->\n</template>"),
    ("comentário de linha em .sh", "publicar.sh",
     "", "set -e\n# limpa a pasta temporária"),
    ("arquivo de teste NÃO é exceção", "src/laco.spec.ts",
     "", "// arruma o dublê antes do caso\nit('soma', () => {})"),
    ("comentário acrescentado a arquivo que já tinha código",
     "src/laco.ts", "const total = 1", "const total = 2\n// agora é dois"),
)

DEIXA_PASSAR = (
    ("shebang", "publicar.sh", "", "#!/usr/bin/env bash\nset -e"),
    ("diretiva do eslint", "src/laco.ts",
     "", "// eslint-disable-next-line no-console\nconsole.log(1)"),
    ("diretiva do TypeScript", "src/laco.ts",
     "", "// @ts-ignore\nconst total = f()"),
    ("noqa do Python", "app/conta.py", "", "import os  # noqa: F401"),
    ("pragma do Python", "app/conta.py",
     "", "# pragma: no cover\ndef f():\n    return 1"),
    ("anotação de tipo em comentário", "app/conta.py",
     "", "# type: ignore\ntotal = f()"),
    ("diretiva do shellcheck", "publicar.sh",
     "", "# shellcheck disable=SC2086\nset -e"),
    ("declaração de codificação do Python", "app/conta.py",
     "", "# -*- coding: utf-8 -*-\ntotal = 1"),
    ("diretiva no template do Vue", "Grade.vue",
     "", "<template>\n  <!-- eslint-disable -->\n</template>"),
    ("arquivo que não é código", "LEIAME.md",
     "", "<!-- explica o repositório -->"),
    ("marca dentro de literal, não no começo da linha", "src/laco.ts",
     "", 'const endereco = "https://exemplo.invalido"'),
    ("comentário que JÁ estava no texto velho", "src/laco.ts",
     "// explica o laço\nconst total = 1",
     "// explica o laço\nconst total = 2"),
    ("diretiva de compilação em .cs, que não é comentário", "Servico.cs",
     "", "#region Consultas\nvar total = 1;\n#endregion"),
    ("código sem comentário nenhum", "app/conta.py",
     "", "def somar(itens):\n    return sum(itens)"),
)


RAZAO_DO_TESTE = "a razão que o veto explicaria"
MODO_DA_SESSAO_INTERATIVA = "default"
SESSAO_INTERATIVA = {CAMPO_DO_MODO_DE_PERMISSAO: MODO_DA_SESSAO_INTERATIVA}
SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA = {
    CAMPO_DO_MODO_DE_PERMISSAO: MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO}
PEDIDO_SEM_MODO_DECLARADO = {}
AMBIENTE_SEM_A_MARCA = {}
AMBIENTE_DA_ETAPA_SEM_NINGUEM = {MARCA_DE_ETAPA_NO_AMBIENTE: "1"}


def testar() -> int:
    diretivas = diretivas_declaradas(raiz_do_projeto_nunca_o_cwd())
    falhas = []
    for rotulo, caminho, velho, novo in BARRA:
        if not comentario_acrescentado(caminho, velho, novo, diretivas):
            falhas.append(FALHA_BARRA.format(rotulo))
    for rotulo, caminho, velho, novo in DEIXA_PASSAR:
        linha = comentario_acrescentado(caminho, velho, novo, diretivas)
        if linha:
            falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, linha))

    comportamento = []

    def caso(rotulo, condicao):
        comportamento.append((rotulo, bool(condicao)))

    def recusou_sem_entender(falha):
        import io
        import contextlib
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            recusa_por_nao_entender(falha)
        try:
            dado = json.loads(saida.getvalue())["hookSpecificOutput"]
        except (ValueError, KeyError):
            return False
        return (dado.get("permissionDecision") == DECISAO_DE_NEGAR
                and type(falha).__name__ in
                dado.get("permissionDecisionReason", ""))

    caso("gancho que veta e não entende o pedido RECUSA, e nomeia a falha — "
         "quem não consegue julgar não pode dizer sim",
         recusou_sem_entender(TypeError("forma que o gancho não conhece")))

    recusa_do_comentario = (
        RECUSA.format("conta.py", "# soma os itens",
                      diretivas_para_a_mensagem(diretivas),
                      ARQUIVO_DAS_DIRETIVAS)
        + MANDA_GRAVAR.format(APRENDIZADO))
    recusa_de_afrouxar = (
        RECUSA_DE_AFROUXAR.format(ARQUIVO_DAS_DIRETIVAS)
        + MANDA_GRAVAR.format(
            APRENDIZADO_DE_AFROUXAR.format(ARQUIVO_DAS_DIRETIVAS)))

    caso("a recusa nomeia a regra 14, diz onde o valor certo mora e manda "
         "gravar o aprendizado em conhecimento/",
         "Regra 14" in recusa_do_comentario
         and ARQUIVO_DAS_DIRETIVAS in recusa_do_comentario
         and "regra 4" in recusa_do_comentario
         and "`conhecimento/`" in recusa_do_comentario)
    caso("a recusa de afrouxar a cerca nomeia a regra 9 e manda gravar",
         "Regra 9" in recusa_de_afrouxar
         and "regra 4" in recusa_de_afrouxar)
    caso("a lista de diretivas é lida do disco — o falha-fechado abaixo "
         "não é arquivo faltando nesta árvore",
         bool(diretivas))
    caso("sem a lista no disco o gancho falha FECHADO: a diretiva que a "
         "lista libera passa a ser negada",
         comentario_acrescentado("app/conta.py", "",
                                 "# pragma: no cover", SEM_DIRETIVAS)
         == "# pragma: no cover")
    caso("sem a lista a recusa nomeia a falta em vez de liberar em "
         "silêncio",
         ARQUIVO_DAS_DIRETIVAS
         in diretivas_para_a_mensagem(SEM_DIRETIVAS))
    caso("shebang passa mesmo sem a lista — quem o julga é o gancho, não "
         "a configuração",
         e_excecao_mecanica("#!/usr/bin/env bash", SEM_DIRETIVAS))
    caso("escrever na lista de exceções é recusado: cerca que quem foi "
         "barrado afrouxa não é cerca",
         escreve_na_lista_das_diretivas(ARQUIVO_DAS_DIRETIVAS))
    caso("arquivo de mesmo nome fora de .claude não é a lista",
         not escreve_na_lista_das_diretivas(
             "tmp/diretivas-de-ferramenta.txt"))

    caso("em modo `default` sem a marca da etapa a resposta do gancho "
         "traz `ask`: o veto pergunta antes, em vez de negar de vez",
         resposta_do_veto(SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                          AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_PERGUNTAR)
    caso("em `bypassPermissions` sem a marca pode haver gente, mas o "
         "cliente não garante mostrar a pergunta do gancho nesse modo: "
         "`deny`, o único jeito de a regra valer",
         resposta_do_veto(SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA,
                          RAZAO_DO_TESTE, AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_NEGAR)
    caso("na etapa do executor, com a marca no ambiente, ninguém "
         "responde nem em modo `default`: `deny`",
         resposta_do_veto(SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                          AMBIENTE_DA_ETAPA_SEM_NINGUEM)
         .get("permissionDecision") == DECISAO_DE_NEGAR)
    caso("pedido que não declara o modo de permissão, sem a marca, "
         "recebe `ask` — nega só a etapa sem ninguém ou o modo que não "
         "mostra a pergunta",
         resposta_do_veto(PEDIDO_SEM_MODO_DECLARADO, RAZAO_DO_TESTE,
                          AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_PERGUNTAR)
    caso("a razão do veto viaja na resposta, com `ask` e com `deny`: é "
         "ela que o prompt de permissão mostra ao dono",
         resposta_do_veto(SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                          AMBIENTE_SEM_A_MARCA)
         .get("permissionDecisionReason") == RAZAO_DO_TESTE
         and resposta_do_veto(SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA,
                              RAZAO_DO_TESTE, AMBIENTE_SEM_A_MARCA)
         .get("permissionDecisionReason") == RAZAO_DO_TESTE)

    with tempfile.TemporaryDirectory(prefix="veto-comentario-") as tmp:
        raiz = Path(tmp)
        (raiz / "src").mkdir()
        alvo = raiz / "src" / "laco.ts"
        alvo.write_text("// explica o laço\nconst total = 1\n",
                        encoding="utf-8")

        def escritas(entrada):
            return escritas_com_texto_do_pedido(entrada, raiz)

        def veredito(entrada):
            return [comentario_acrescentado(c, v, n, diretivas)
                    for c, v, n in escritas(entrada)]

        caso("Write compara com o que já está no disco",
             veredito({"tool_name": "Write", "tool_input": {
                 "file_path": "src/laco.ts",
                 "content": "// explica o laço\nconst total = 2\n"}})
             == [PASSA])
        caso("Write que acrescenta comentário ao que estava no disco barra",
             veredito({"tool_name": "Write", "tool_input": {
                 "file_path": "src/laco.ts",
                 "content": "// explica o laço\n// e agora dois\n"}})
             == ["// e agora dois"])
        caso("Write em arquivo que não existe trata tudo como novo",
             veredito({"tool_name": "Write", "tool_input": {
                 "file_path": "src/novo.ts",
                 "content": "// nasce comentado"}}) == ["// nasce comentado"])
        caso("Edit é alcançado",
             veredito({"tool_name": "Edit", "tool_input": {
                 "file_path": "src/laco.ts", "old_string": "const total = 1",
                 "new_string": "// dobra o total\nconst total = 2"}})
             == ["// dobra o total"])
        caso("MultiEdit alcança cada edição",
             veredito({"tool_name": "MultiEdit", "tool_input": {
                 "file_path": "src/laco.ts", "edits": [
                     {"old_string": "a", "new_string": "b"},
                     {"old_string": "c", "new_string": "// terceira"}]}})
             == [PASSA, "// terceira"])
        caso("ferramenta fora do veto não devolve escrita",
             escritas({"tool_name": "Bash", "tool_input": {
                 "command": "echo '// explica' >> src/laco.ts"}}) == [])
        caso("pedido sem caminho não devolve escrita",
             escritas({"tool_name": "Write", "tool_input": {
                 "content": "// explica"}}) == [])
        caso("entrada quebrada não prende a sessão", escritas({}) == [])
        caso("edição malformada no MultiEdit não derruba o gancho",
             escritas({"tool_name": "MultiEdit", "tool_input": {
                 "file_path": "src/laco.ts", "edits": ["nada"]}}) == [])

    with tempfile.TemporaryDirectory(prefix="veto-docstring-") as tmp, \
            tempfile.TemporaryDirectory(prefix="veto-docstring-fora-") as fora:
        raiz = (Path(tmp).resolve() / "arvore")
        raiz.mkdir()
        (raiz / ".git").mkdir()
        (raiz / "app").mkdir()
        vizinho = raiz / "projetos" / "vizinho"
        vizinho.mkdir(parents=True)
        (vizinho / ".git").mkdir()
        com_docstring = 'def somar(itens):\n    """soma os itens"""\n    return sum(itens)\n'
        de_modulo = '"""o módulo que conta"""\nimport os\n'
        sem_docstring = "def somar(itens):\n    return sum(itens)\n"

        def docstring(caminho, velho, novo):
            return docstring_acrescentada(caminho, velho, novo, raiz)

        caso("docstring de função em arquivo da raiz da camada barra, e a "
             "recusa mostra a linha",
             docstring("app/conta.py", "", com_docstring)
             == '"""soma os itens"""')
        caso("docstring de módulo na raiz da camada barra — o ritual a "
             "reprovava e a cerca deixava passar",
             docstring("app/conta.py", "", de_modulo)
             == '"""o módulo que conta"""')
        caso("caminho absoluto dentro da raiz também é território da camada",
             docstring(str(raiz / "app" / "conta.py"), "", com_docstring)
             == '"""soma os itens"""')
        caso("docstring dentro de repositório vizinho (projetos/<nome>, com "
             ".git próprio) passa — lá docstring é normal",
             docstring("projetos/vizinho/x.py", "", com_docstring) == PASSA)
        arvore = raiz / "projetos" / "arvore-de-trabalho"
        arvore.mkdir(parents=True)
        (arvore / MARCA_DE_REPOSITORIO_VIZINHO).write_text(
            "gitdir: /outro/lugar/.git/worktrees/arvore-de-trabalho\n",
            encoding="utf-8")
        caso("vizinho cujo .git é ARQUIVO — árvore de trabalho do git, ou "
             "submódulo — também é território de terceiro: o julgamento "
             "pergunta se o caminho EXISTE, nunca se é pasta",
             docstring("projetos/arvore-de-trabalho/x.py", "", com_docstring)
             == PASSA
             and not dentro_da_raiz_da_camada(
                 "projetos/arvore-de-trabalho/x.py", raiz))
        ao_lado = raiz.parent / (raiz.name + "-ao-lado")
        (ao_lado / "app").mkdir(parents=True, exist_ok=True)
        (ao_lado / MARCA_DE_REPOSITORIO).write_text(
            "gitdir: /outro/lugar\n", encoding="utf-8")
        vizinho_de_la = ao_lado / "projetos" / "vizinho"
        vizinho_de_la.mkdir(parents=True, exist_ok=True)
        (vizinho_de_la / MARCA_DE_REPOSITORIO).mkdir(exist_ok=True)
        caso("docstring em OUTRA árvore de trabalho da camada barra — a raiz "
             "sai do alvo, e antes disso a cerca calava em toda worktree",
             docstring_acrescentada(
                 str(ao_lado / "app" / "conta.py"), "", com_docstring,
                 raiz_do_alvo(str(ao_lado / "app" / "conta.py"), raiz)))
        caso("e o vizinho com git próprio DENTRO da outra árvore continua "
             "livre: território de terceiro não muda de dono por estar numa "
             "worktree",
             not docstring_acrescentada(
                 str(vizinho_de_la / "x.py"), "", com_docstring,
                 raiz_do_alvo(str(vizinho_de_la / "x.py"), raiz)))

        caso("docstring em caminho fora da raiz da camada passa",
             docstring(str(Path(fora) / "x.py"), "", com_docstring) == PASSA)
        caso("comentário em caminho fora da raiz e sem repositório acima é "
             "script descartável: a cerca de comentário cala",
             fora_de_todo_repositorio(str(Path(fora) / "x.py"), raiz))
        caso("caminho relativo é da raiz da camada: a cerca de comentário "
             "continua valendo",
             not fora_de_todo_repositorio("app/conta.py", raiz))
        caso("caminho absoluto dentro da raiz continua valendo",
             not fora_de_todo_repositorio(str(raiz / "app" / "conta.py"),
                                          raiz))
        caso("repositório fora da raiz, com .git acima, continua valendo",
             not fora_de_todo_repositorio(str(vizinho_de_la / "x.py"), raiz))
        caso("código sem docstring na raiz passa",
             docstring("app/conta.py", "", sem_docstring) == PASSA)
        caso("`# noqa` continua passando: não é docstring nem comentário "
             "barrado",
             docstring("app/conta.py", "", "import os  # noqa: F401\n")
             == PASSA
             and not comentario_acrescentado(
                 "app/conta.py", "", "import os  # noqa: F401\n", diretivas))
        caso("docstring em arquivo que não é Python passa",
             docstring("app/LEIAME.md", "", com_docstring) == PASSA)
        caso("string tripla atribuída a um nome não é docstring",
             docstring("app/conta.py", "",
                       'TEXTO = """\nlinha um\nlinha dois\n"""\n') == PASSA)
        no_disco = raiz / "app" / "conta.py"
        no_disco.write_text(sem_docstring, encoding="utf-8")
        caso("Edit que acrescenta docstring a função que já está no disco "
             "barra — o texto inteiro é remontado e lido pela árvore",
             docstring("app/conta.py", "def somar(itens):\n    return",
                       'def somar(itens):\n    """soma"""\n    return')
             == '"""soma"""')
        caso("Edit cujo texto velho não casa com o disco cai na heurística: "
             "aspas logo após a linha de def barram",
             docstring("app/conta.py", "    return 1",
                       'def dobrar(x):\n    """dobra"""\n    return 2 * x')
             == '"""dobra"""')
        no_disco.write_text("import os\n" + sem_docstring, encoding="utf-8")
        caso("Edit que planta docstring de módulo antes do primeiro import "
             "barra pela árvore — a heurística não enxerga o topo do arquivo "
             "num fragmento sem recuo",
             docstring("app/conta.py", "import os",
                       '"""o módulo"""\nimport os') == '"""o módulo"""')
        caso("fragmento que é corpo de função e abre com aspas triplas barra",
             docstring("app/conta.py", "    return sum(itens)",
                       '    """soma tudo"""\n    return sum(itens)')
             == '"""soma tudo"""')
        caso("docstring de uma linha com aspas simples logo após o def barra",
             docstring("app/conta.py", "",
                       "def f():\n    'explica'\n    return 1\n")
             == "'explica'")
        no_disco.write_text(
            'MOLDE = """\nlinha velha\n"""\ndef f():\n    return 1\n',
            encoding="utf-8")
        caso("Edit que só troca o miolo de uma string tripla atribuída passa "
             "— o texto remontado não ganhou docstring nenhuma",
             docstring("app/conta.py", '"""\nlinha velha\n"""',
                       '"""\nlinha nova\n"""') == PASSA)
        no_disco.write_text(com_docstring, encoding="utf-8")
        caso("Write que repete a docstring que JÁ estava no disco não é "
             "acréscimo",
             docstring("app/conta.py", com_docstring, com_docstring) == PASSA)
        caso("a recusa da docstring nomeia a regra 14, diz que é comentário "
             "na régua da casa e manda gravar o aprendizado",
             "Regra 14" in RECUSA_DE_DOCSTRING
             and "comentário explicativo" in RECUSA_DE_DOCSTRING
             and "regra 4" in MANDA_GRAVAR.format(APRENDIZADO_DA_DOCSTRING))
        caso("a raiz do julgamento é a da camada, nunca o cwd: arquivo dentro "
             "dela é território mesmo com o processo rodando em outra pasta",
             dentro_da_raiz_da_camada("app/conta.py", raiz)
             and not dentro_da_raiz_da_camada("projetos/vizinho/x.py", raiz)
             and not dentro_da_raiz_da_camada(str(Path(fora) / "x.py"), raiz))

    falhas += [FALHA_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]

    total = len(BARRA) + len(DEIXA_PASSAR) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR),
                           len(comportamento)))
    return 0


def resposta_do_veto(entrada: dict, razao: str, ambiente) -> dict:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        vetar(entrada, razao, ambiente)
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
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
