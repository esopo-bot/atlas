import json
import os
import re
import shlex
import sys
from pathlib import Path

MARCAS_DO_CORPO_DA_ISSUE = ("## Critério de aceitação", "## Onde mexer",
                            "## Ponto de retomada", "## Estado")
MINIMO_DE_MARCAS = 2
EXTENSOES_DE_ANDAMENTO = (".md", ".txt")
PASTA_DO_ENCERRAMENTO = "conhecimento"
PASTA_DOS_MOLDES = "references"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
CAMPOS_DE_TEXTO = ("content", "new_string", "new_source")
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&]+)")
COMANDOS_QUE_ESCREVEM_SEM_SETA = ("tee", "cp", "mv", "install", "touch")

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
APRENDIZADO = (
    "andamento de trabalho não nasce em arquivo: o corpo da issue é o "
    "estado, e o `.md` só no encerramento, para extrair o que vale adiante."
)

MOTIVO_NASCE_COMO_CORPO_DE_ISSUE = (
    "criar {!r}, que já nasce com o corpo de uma issue — as seções {}")
RECUSA = (
    "Regra 4 da camada: isto quer {}. O estado do trabalho mora NA ISSUE, "
    "não num arquivo do disco: arquivo de andamento vira uma segunda "
    "verdade, e é ela que mente para a próxima sessão, porque ninguém a "
    "atualiza junto. Escreva o andamento na issue — o corpo é o estado, o "
    "comentário é o evento. O `.md` só entra no ENCERRAMENTO, para extrair "
    "o que vale adiante, e aí ele nasce em `{}/`. Rascunho de corpo de "
    "issue não precisa virar arquivo daqui: mande o texto direto para a "
    "issue, ou escreva-o fora deste repositório."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def marcas_de_corpo_de_issue(texto: str) -> list:
    return [marca for marca in MARCAS_DO_CORPO_DA_ISSUE if marca in texto]


def e_arquivo_de_andamento(caminho: str) -> bool:
    return caminho.lower().endswith(EXTENSOES_DE_ANDAMENTO)


def e_o_encerramento_ou_um_molde(alvo: Path, raiz: Path) -> bool:
    try:
        partes = alvo.relative_to(raiz).parts
    except ValueError:
        return True
    return (PASTA_DO_ENCERRAMENTO in partes) or (PASTA_DOS_MOLDES in partes)


def motivo_da_recusa(caminho: str, texto: str, raiz: Path) -> str:
    if not caminho or not texto:
        return PASSA
    if not e_arquivo_de_andamento(caminho):
        return PASSA
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = raiz / alvo
    try:
        alvo = alvo.resolve(strict=False)
    except OSError:
        return PASSA
    e_edicao_do_que_ja_existe = alvo.exists()
    if e_edicao_do_que_ja_existe:
        return PASSA
    if e_o_encerramento_ou_um_molde(alvo, raiz.resolve(strict=False)):
        return PASSA
    marcas = marcas_de_corpo_de_issue(texto)
    if len(marcas) < MINIMO_DE_MARCAS:
        return PASSA
    return MOTIVO_NASCE_COMO_CORPO_DE_ISSUE.format(
        alvo.name, ", ".join(f"`{marca}`" for marca in marcas))


def texto_que_o_pedido_escreveria(entrada: dict) -> str:
    dado = entrada.get("tool_input", {}) or {}
    if entrada.get("tool_name", "") in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_TEXTO:
            if dado.get(campo):
                return str(dado[campo])
        return ""
    return str(dado.get("command", ""))


def caminhos_que_o_pedido_criaria(entrada: dict) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [dado[campo]]
        return []
    comando = dado.get("command", "")
    if not comando:
        return []
    achados = [m.group(1) for m in REDIRECIONAMENTO_DE_SHELL.finditer(comando)]
    try:
        pedacos = shlex.split(comando)
    except ValueError:
        pedacos = comando.split()
    if pedacos and Path(pedacos[0]).name in COMANDOS_QUE_ESCREVEM_SEM_SETA:
        achados += pedacos[1:]
    return [a.strip("\"'") for a in achados if a and not a.startswith("-")]


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
    texto = texto_que_o_pedido_escreveria(entrada)
    for caminho in caminhos_que_o_pedido_criaria(entrada):
        motivo = motivo_da_recusa(caminho, texto, raiz)
        if motivo:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": (
                    RECUSA.format(motivo, PASTA_DO_ENCERRAMENTO)
                    + MANDA_GRAVAR.format(APRENDIZADO)),
            }}, ensure_ascii=False))
            return SILENCIO
    return SILENCIO


CORPO_DE_ISSUE = (
    "## Objetivo\n\nfazer o relatório fechar\n\n"
    "## Critério de aceitação\n\n- [ ] o total bate\n\n"
    "## Ponto de retomada\n\nFaça agora: leia o extrato\n")
UMA_MARCA_SO = "## Estado\n\na medição de ontem\n"


def montar_workspace_de_mentira(pasta: Path):
    (pasta / PASTA_DO_ENCERRAMENTO).mkdir(parents=True, exist_ok=True)
    (pasta / "tmp").mkdir(exist_ok=True)
    (pasta / ".agents" / "skills" / "s" / PASTA_DOS_MOLDES).mkdir(
        parents=True, exist_ok=True)
    (pasta / "ja-existe.md").write_text(CORPO_DE_ISSUE, encoding="utf-8")
    return pasta


BARRA = [
    ("corpo de issue nascendo na raiz", "andamento.md", CORPO_DE_ISSUE),
    ("corpo de issue nascendo no descartável", "tmp/estado.md",
     CORPO_DE_ISSUE),
    ("corpo de issue nascendo em pasta de projeto", "projetos/app/onde-parei.md",
     CORPO_DE_ISSUE),
    ("corpo de issue em .txt", "notas.txt", CORPO_DE_ISSUE),
]

DEIXA_PASSAR = [
    ("a lição do encerramento, em conhecimento/",
     "conhecimento/o-que-o-caso-ensinou.md", CORPO_DE_ISSUE),
    ("o molde da skill, em references/",
     ".agents/skills/s/references/moldes.md", CORPO_DE_ISSUE),
    ("página com UMA seção só, abaixo do mínimo", "nota.md", UMA_MARCA_SO),
    ("arquivo que JÁ EXISTE", "ja-existe.md", CORPO_DE_ISSUE),
    ("código, que não é arquivo de andamento", "medir.py", CORPO_DE_ISSUE),
    ("arquivo fora deste repositório", "/tmp/rascunho-de-fora.md",
     CORPO_DE_ISSUE),
    ("arquivo de andamento sem texto nenhum", "andamento.md", ""),
]


def testar() -> int:
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory(prefix="veto-andamento-") as tmp:
        raiz = montar_workspace_de_mentira(Path(tmp))
        for rotulo, caminho, texto in BARRA:
            if not motivo_da_recusa(caminho, texto, raiz):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, caminho, texto in DEIXA_PASSAR:
            motivo = motivo_da_recusa(caminho, texto, raiz)
            if motivo:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, motivo))

        comportamento = []

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        caso("gancho que veta e não entende o pedido RECUSA, e nomeia a "
             "falha — quem não consegue julgar não pode dizer sim",
             recusou_sem_entender(TypeError("forma que o gancho não conhece")))

        mensagem = (RECUSA.format(MOTIVO_NASCE_COMO_CORPO_DE_ISSUE.format(
            "andamento.md", "`## Estado`"), PASTA_DO_ENCERRAMENTO)
            + MANDA_GRAVAR.format(APRENDIZADO))
        caso("a recusa nomeia a regra 4, diz que o estado mora na issue, "
             "abre a exceção do encerramento e manda gravar o aprendizado",
             "Regra 4" in mensagem and "NA ISSUE" in mensagem
             and "ENCERRAMENTO" in mensagem and "regra 4" in mensagem
             and APRENDIZADO in mensagem)
        caso("a recusa nomeia as seções que a acusaram",
             "`## Estado`" in mensagem)

        caso("a ferramenta Write entrega caminho e texto",
             caminhos_que_o_pedido_criaria({
                 "tool_name": "Write",
                 "tool_input": {"file_path": "andamento.md",
                                "content": CORPO_DE_ISSUE}}) == ["andamento.md"]
             and texto_que_o_pedido_escreveria({
                 "tool_name": "Write",
                 "tool_input": {"file_path": "andamento.md",
                                "content": CORPO_DE_ISSUE}}) == CORPO_DE_ISSUE)
        caso("a ferramenta Edit entrega o texto acrescentado",
             texto_que_o_pedido_escreveria({
                 "tool_name": "Edit",
                 "tool_input": {"file_path": "a.md",
                                "new_string": CORPO_DE_ISSUE}})
             == CORPO_DE_ISSUE)
        caso("o heredoc do shell é alcançado, caminho e corpo",
             caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash",
                 "tool_input": {"command":
                                "cat > andamento.md <<'EOF'\n"
                                + CORPO_DE_ISSUE + "EOF"}})
             == ["andamento.md"]
             and "## Ponto de retomada" in texto_que_o_pedido_escreveria({
                 "tool_name": "Bash",
                 "tool_input": {"command":
                                "cat > andamento.md <<'EOF'\n"
                                + CORPO_DE_ISSUE + "EOF"}}))
        caso("comando que só lê não devolve alvo",
             caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash",
                 "tool_input": {"command": "cat andamento.md"}}) == [])
        caso("entrada quebrada não prende a sessão (falha aberto)",
             caminhos_que_o_pedido_criaria({}) == []
             and texto_que_o_pedido_escreveria({}) == "")
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash", "tool_input": {
                     "command": "echo 'sem fechar > andamento.md"}}), list))
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
