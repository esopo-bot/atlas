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

FERRAMENTA_DE_ESCRITA_INTEIRA = "Write"
FERRAMENTA_DE_UMA_EDICAO = "Edit"
FERRAMENTA_DE_VARIAS_EDICOES = "MultiEdit"
CAMPO_DO_CAMINHO = "file_path"
CAMPO_DO_CONTEUDO = "content"
CAMPO_DO_TEXTO_VELHO = "old_string"
CAMPO_DO_TEXTO_NOVO = "new_string"
CAMPO_DAS_EDICOES = "edits"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
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
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    diretivas = diretivas_declaradas(raiz)
    for caminho, velho, novo in escritas_com_texto_do_pedido(entrada, raiz):
        if escreve_na_lista_das_diretivas(caminho):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": (
                    RECUSA_DE_AFROUXAR.format(ARQUIVO_DAS_DIRETIVAS)
                    + MANDA_GRAVAR.format(APRENDIZADO_DE_AFROUXAR.format(
                        ARQUIVO_DAS_DIRETIVAS))),
            }}, ensure_ascii=False))
            return SILENCIO
        linha = comentario_acrescentado(caminho, velho, novo, diretivas)
        if linha:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": (
                    RECUSA.format(
                        Path(caminho).name, linha,
                        diretivas_para_a_mensagem(diretivas),
                        ARQUIVO_DAS_DIRETIVAS)
                    + MANDA_GRAVAR.format(APRENDIZADO)),
            }}, ensure_ascii=False))
            return SILENCIO
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


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
